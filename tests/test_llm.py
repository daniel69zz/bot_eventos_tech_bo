"""Filtro LLM: lotes, tolerancia a fallos, dedup por evento y orden por fecha."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import config
from filtros import llm

_TZ = timezone(timedelta(hours=-4))


def _hoy():
    return datetime.now(_TZ).date()


def _fecha(dias: int) -> str:
    return (_hoy() + timedelta(days=dias)).isoformat()


def _candidato(titulo, fuente="Web", url=None):
    return {"titulo": titulo, "snippet": "", "fuente": fuente,
            "url": url or f"https://ejemplo.bo/{titulo}"}


def _respuesta_llm(eventos):
    """Simula la respuesta HTTP de una API estilo OpenAI."""
    contenido = json.dumps({"eventos": eventos})
    falsa = mock.Mock()
    falsa.json.return_value = {"choices": [{"message": {"content": contenido}}]}
    return falsa


class TestParsearFecha(unittest.TestCase):
    def test_fecha_valida(self):
        self.assertEqual(llm._parsear_fecha("2026-08-20").isoformat(), "2026-08-20")

    def test_valores_invalidos(self):
        for valor in ("desconocida", "", None, "20/08/2026", "2026-13-45"):
            with self.subTest(valor=valor):
                self.assertIsNone(llm._parsear_fecha(valor))


class TestOrdenarPorFecha(unittest.TestCase):
    def test_futuros_primero_y_mas_proximo_arriba(self):
        eventos = [{"fecha": _fecha(10), "titulo": "lejano"},
                   {"fecha": _fecha(1), "titulo": "proximo"}]
        self.assertEqual([e["titulo"] for e in llm._ordenar_por_fecha(eventos)],
                         ["proximo", "lejano"])

    def test_orden_futuros_luego_desconocidos_luego_pasados(self):
        eventos = [{"fecha": "desconocida", "titulo": "sin fecha"},
                   {"fecha": _fecha(-2), "titulo": "pasado"},
                   {"fecha": _fecha(3), "titulo": "futuro"}]
        self.assertEqual([e["titulo"] for e in llm._ordenar_por_fecha(eventos)],
                         ["futuro", "sin fecha", "pasado"])

    def test_descarta_pasados_muy_viejos(self):
        eventos = [{"fecha": _fecha(-(llm.DIAS_PASADO_MAX + 1)), "titulo": "viejo"}]
        self.assertEqual(llm._ordenar_por_fecha(eventos), [])

    def test_agrega_fecha_dt(self):
        [evento] = llm._ordenar_por_fecha([{"fecha": _fecha(1), "titulo": "x"}])
        self.assertEqual(evento["fecha_dt"], _hoy() + timedelta(days=1))


class TestDedupPorEvento(unittest.TestCase):
    def test_misma_clave_se_colapsa_prefiriendo_mejor_fuente(self):
        eventos = [{"clave": "hackathon-2026", "fuente": "TikTok"},
                   {"clave": "hackathon-2026", "fuente": "Luma"},
                   {"clave": "hackathon-2026", "fuente": "Facebook"}]
        unicos = llm._dedup_por_evento(eventos)
        self.assertEqual(len(unicos), 1)
        self.assertEqual(unicos[0]["fuente"], "Luma")

    def test_claves_distintas_se_mantienen(self):
        eventos = [{"clave": "a", "fuente": "Web"}, {"clave": "b", "fuente": "Web"}]
        self.assertEqual(len(llm._dedup_por_evento(eventos)), 2)

    def test_sin_clave_no_se_colapsa(self):
        eventos = [{"clave": "", "fuente": "Web"}, {"clave": "", "fuente": "Web"}]
        self.assertEqual(len(llm._dedup_por_evento(eventos)), 2)


class TestFiltrar(unittest.TestCase):
    def setUp(self):
        parche = mock.patch.object(config, "LLM_API_KEY", "clave-de-prueba")
        parche.start()
        self.addCleanup(parche.stop)

    def test_sin_candidatos(self):
        self.assertEqual(llm.filtrar([]), ([], []))

    def test_sin_api_key_no_avisa_ni_marca_nada(self):
        # Antes se mandaban los candidatos SIN filtrar a Telegram.
        with mock.patch.object(config, "LLM_API_KEY", ""):
            self.assertEqual(llm.filtrar([_candidato("algo")]), ([], []))

    def test_devuelve_solo_los_confirmados(self):
        candidatos = [_candidato("hackathon"), _candidato("basura")]
        respuesta = _respuesta_llm([
            {"indice": 0, "es_evento": True, "ciudad": "La Paz", "clave": "h",
             "fecha": _fecha(3), "resumen": "Hackathon en La Paz", "descripcion": "d"},
            {"indice": 1, "es_evento": False},
        ])
        with mock.patch.object(llm.red, "pedir", return_value=respuesta):
            eventos, procesados = llm.filtrar(candidatos)
        self.assertEqual([e["resumen"] for e in eventos], ["Hackathon en La Paz"])
        self.assertEqual(len(procesados), 2)  # los 2 se evaluaron, aunque uno no pase

    def test_indice_fuera_de_rango_se_ignora(self):
        respuesta = _respuesta_llm([{"indice": 99, "es_evento": True, "resumen": "fantasma"}])
        with mock.patch.object(llm.red, "pedir", return_value=respuesta):
            eventos, _ = llm.filtrar([_candidato("uno")])
        self.assertEqual(eventos, [])

    def test_fecha_y_ciudad_oficiales_ganan_sobre_las_del_modelo(self):
        candidato = _candidato("charla", fuente="Luma")
        candidato["fecha_oficial"] = _fecha(5)
        candidato["ciudad_oficial"] = "La Paz"
        respuesta = _respuesta_llm([{"indice": 0, "es_evento": True, "ciudad": "Santa Cruz",
                                     "clave": "c", "fecha": _fecha(30), "resumen": "Charla"}])
        with mock.patch.object(llm.red, "pedir", return_value=respuesta):
            [evento], _ = llm.filtrar([candidato])
        self.assertEqual(evento["ciudad"], "La Paz")
        self.assertEqual(evento["fecha"], _fecha(5))

    def test_parte_en_lotes(self):
        candidatos = [_candidato(f"e{i}") for i in range(5)]
        with mock.patch.object(config, "LOTE_LLM", 2), \
             mock.patch.object(llm.red, "pedir", return_value=_respuesta_llm([])) as pedir:
            llm.filtrar(candidatos)
        self.assertEqual(pedir.call_count, 3)  # 2 + 2 + 1

    def test_lote_fallido_no_se_marca_como_procesado(self):
        candidatos = [_candidato(f"e{i}") for i in range(4)]
        ok = _respuesta_llm([{"indice": 0, "es_evento": True, "clave": "a",
                              "fecha": _fecha(2), "resumen": "bueno"}])
        with mock.patch.object(config, "LOTE_LLM", 2), \
             mock.patch.object(llm.red, "pedir", side_effect=[ok, RuntimeError("429")]):
            eventos, procesados = llm.filtrar(candidatos)
        # El primer lote se procesó; el segundo se reintenta en la próxima corrida.
        self.assertEqual([c["titulo"] for c in procesados], ["e0", "e1"])
        self.assertEqual([e["resumen"] for e in eventos], ["bueno"])

    def test_json_invalido_no_marca_el_lote(self):
        rota = mock.Mock()
        rota.json.return_value = {"choices": [{"message": {"content": "no soy json"}}]}
        with mock.patch.object(llm.red, "pedir", return_value=rota):
            eventos, procesados = llm.filtrar([_candidato("uno")])
        self.assertEqual((eventos, procesados), ([], []))


if __name__ == "__main__":
    unittest.main()
