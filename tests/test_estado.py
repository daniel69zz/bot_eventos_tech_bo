"""Estado persistente: caducidad, páginas hub, migración del formato viejo y rotación."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

import config
import estado


def _hace(dias: int) -> str:
    return (datetime.now().date() - timedelta(days=dias)).isoformat()


class BaseEstado(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.archivo = os.path.join(self.dir.name, "enviados.json")
        parche = mock.patch.object(estado, "ARCHIVO", self.archivo)
        parche.start()
        self.addCleanup(parche.stop)

    def escribir(self, datos):
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f)

    def leer(self):
        with open(self.archivo, encoding="utf-8") as f:
            return json.load(f)


class TestEsHub(unittest.TestCase):
    def test_paginas_de_cuenta_son_hub(self):
        for url in ("https://www.facebook.com/GDGLaPaz",
                    "https://instagram.com/pythonbolivia",
                    "https://www.tiktok.com/@techbolivia",
                    "https://www.meetup.com/gdg-la-paz/",
                    "https://www.eventbrite.com/o/comunidad-tech-123"):
            with self.subTest(url=url):
                self.assertTrue(estado.es_hub(url))

    def test_paginas_de_evento_concreto_no_son_hub(self):
        for url in ("https://www.facebook.com/events/123456789/",
                    "https://www.meetup.com/gdg-la-paz/events/301234567/",
                    "https://lu.ma/abc123",
                    "https://www.instagram.com/p/CxYz123/",
                    "https://algunauniversidad.edu.bo/charla-ia"):
            with self.subTest(url=url):
                self.assertFalse(estado.es_hub(url))


class TestMigracionYPurga(BaseEstado):
    def test_lee_formato_viejo_de_lista(self):
        self.escribir(["https://ejemplo.bo/a", "https://ejemplo.bo/b"])
        self.assertEqual(set(estado.cargar()), {"https://ejemplo.bo/a", "https://ejemplo.bo/b"})

    def test_migra_a_formato_nuevo_al_guardar(self):
        self.escribir(["https://ejemplo.bo/a"])
        estado.marcar_enviados([{"url": "https://ejemplo.bo/b"}])
        datos = self.leer()
        self.assertEqual(datos["version"], 2)
        self.assertEqual(set(datos["urls"]), {"https://ejemplo.bo/a", "https://ejemplo.bo/b"})

    def test_archivo_inexistente_o_corrupto_no_revienta(self):
        self.assertEqual(estado.cargar(), {})
        with open(self.archivo, "w", encoding="utf-8") as f:
            f.write("{no es json")
        self.assertEqual(estado.cargar(), {})

    def test_purga_urls_viejas(self):
        self.escribir({"version": 2, "rotacion": 0, "urls": {
            "https://ejemplo.bo/vieja": _hace(config.DIAS_RETENCION_ESTADO + 5),
            "https://ejemplo.bo/nueva": _hace(1),
        }})
        self.assertEqual(set(estado.cargar()), {"https://ejemplo.bo/nueva"})


class TestFiltrarNuevos(BaseEstado):
    def test_url_ya_procesada_se_omite(self):
        self.escribir({"version": 2, "rotacion": 0,
                       "urls": {"https://ejemplo.bo/a": _hace(1)}})
        nuevos = estado.filtrar_nuevos([{"url": "https://ejemplo.bo/a"},
                                        {"url": "https://ejemplo.bo/b"}])
        self.assertEqual([n["url"] for n in nuevos], ["https://ejemplo.bo/b"])

    def test_duplicados_dentro_de_la_misma_corrida(self):
        nuevos = estado.filtrar_nuevos([{"url": "https://ejemplo.bo/a"},
                                        {"url": "https://ejemplo.bo/a"}])
        self.assertEqual(len(nuevos), 1)

    def test_hub_se_revisita_pasados_los_dias(self):
        hub = "https://www.facebook.com/GDGLaPaz"
        self.escribir({"version": 2, "rotacion": 0,
                       "urls": {hub: _hace(config.DIAS_REVISITA_HUB + 1)}})
        self.assertEqual(len(estado.filtrar_nuevos([{"url": hub}])), 1)

    def test_hub_reciente_no_se_revisita(self):
        hub = "https://www.facebook.com/GDGLaPaz"
        self.escribir({"version": 2, "rotacion": 0, "urls": {hub: _hace(1)}})
        self.assertEqual(estado.filtrar_nuevos([{"url": hub}]), [])

    def test_evento_concreto_no_se_revisita_a_los_pocos_dias(self):
        url = "https://lu.ma/abc123"
        self.escribir({"version": 2, "rotacion": 0,
                       "urls": {url: _hace(config.DIAS_REVISITA_HUB + 1)}})
        self.assertEqual(estado.filtrar_nuevos([{"url": url}]), [])


class TestMarcarEnviados(BaseEstado):
    def test_marca_con_la_fecha_de_hoy(self):
        estado.marcar_enviados([{"url": "https://ejemplo.bo/a"}])
        self.assertEqual(self.leer()["urls"]["https://ejemplo.bo/a"],
                         datetime.now().date().isoformat())

    def test_lista_vacia_no_crea_archivo(self):
        estado.marcar_enviados([])
        self.assertFalse(os.path.exists(self.archivo))

    def test_no_marca_lo_que_no_se_le_pasa(self):
        # Si un lote del LLM falla, esos candidatos no llegan acá y se reintentan.
        estado.marcar_enviados([{"url": "https://ejemplo.bo/procesada"}])
        self.assertNotIn("https://ejemplo.bo/fallida", self.leer()["urls"])


class TestRotacion(BaseEstado):
    def test_bloques_consecutivos_y_circulares(self):
        self.assertEqual(estado.siguiente_bloque(10, 4), [0, 1, 2, 3])
        self.assertEqual(estado.siguiente_bloque(10, 4), [4, 5, 6, 7])
        self.assertEqual(estado.siguiente_bloque(10, 4), [8, 9, 0, 1])

    def test_cantidad_cero_devuelve_todas(self):
        self.assertEqual(estado.siguiente_bloque(3, 0), [0, 1, 2])

    def test_cantidad_mayor_al_total_devuelve_todas(self):
        self.assertEqual(estado.siguiente_bloque(3, 99), [0, 1, 2])

    def test_sin_queries_no_revienta(self):
        self.assertEqual(estado.siguiente_bloque(0, 5), [])

    def test_la_rotacion_convive_con_las_urls(self):
        estado.marcar_enviados([{"url": "https://ejemplo.bo/a"}])
        estado.siguiente_bloque(10, 4)
        datos = self.leer()
        self.assertEqual(datos["rotacion"], 4)
        self.assertIn("https://ejemplo.bo/a", datos["urls"])


if __name__ == "__main__":
    unittest.main()
