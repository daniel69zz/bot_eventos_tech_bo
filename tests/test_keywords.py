"""Filtro barato de keywords: evento + lugar, por palabra completa."""
import unittest

from filtros import keywords


def _r(titulo, snippet="", fuente="Web"):
    return {"titulo": titulo, "snippet": snippet, "fuente": fuente}


class TestPasaFiltro(unittest.TestCase):
    def test_evento_y_lugar_pasan(self):
        self.assertTrue(keywords.pasa_filtro(_r("Hackathon de IA", "en La Paz, Bolivia")))

    def test_sin_lugar_no_pasa(self):
        self.assertFalse(keywords.pasa_filtro(_r("Hackathon de IA", "en Lima")))

    def test_sin_keyword_de_evento_no_pasa(self):
        self.assertFalse(keywords.pasa_filtro(_r("Noticias de fútbol", "La Paz, Bolivia")))

    def test_plurales_de_formatos_de_charla(self):
        # "charla" no matchea "charlas" (el match es por palabra completa), así
        # que los plurales tienen que estar listados aparte.
        for titulo in ("Charlas de tecnología", "Talleres de Python", "Conferencias tech"):
            with self.subTest(titulo=titulo):
                self.assertTrue(keywords.pasa_filtro(_r(titulo, "Cochabamba")))

    def test_formatos_de_charla_nuevos(self):
        for titulo in ("Conversatorio sobre IA", "Ciclo de charlas de software",
                       "Mesa redonda de ciberseguridad", "Conferencia magistral de datos"):
            with self.subTest(titulo=titulo):
                self.assertTrue(keywords.pasa_filtro(_r(titulo, "La Paz")))

    def test_acronimo_corto_no_matchea_dentro_de_otra_palabra(self):
        # "ia" no debe matchear dentro de "familia"
        self.assertFalse(keywords.pasa_filtro(_r("Historia de la familia", "La Paz")))

    def test_zona_de_la_paz_cuenta_como_lugar(self):
        self.assertTrue(keywords.pasa_filtro(_r("Meetup de Python", "Auditorio en Sopocachi")))

    def test_acentos_y_mayusculas_son_indiferentes(self):
        self.assertTrue(keywords.pasa_filtro(_r("CONFERENCIA de Programación", "LA PAZ")))

    def test_luma_no_exige_lugar_en_el_snippet(self):
        # El snippet de lu.ma casi nunca trae ciudad; el lugar lo confirma
        # después fuentes/detalle.py.
        sin_lugar = _r("Meetup de Python", "Sin ciudad en el snippet", fuente="Luma")
        self.assertTrue(keywords.pasa_filtro(sin_lugar))
        self.assertFalse(keywords.pasa_filtro({**sin_lugar, "fuente": "Web"}))

    def test_luma_igual_exige_keyword_de_evento(self):
        self.assertFalse(keywords.pasa_filtro(_r("Página personal", "nada", fuente="Luma")))


class TestFiltrar(unittest.TestCase):
    def test_devuelve_solo_los_que_pasan(self):
        entrada = [
            _r("Hackathon", "Santa Cruz"),
            _r("Receta de cocina", "La Paz"),
            _r("Bootcamp de datos", "UMSA"),
        ]
        self.assertEqual(len(keywords.filtrar(entrada)), 2)


if __name__ == "__main__":
    unittest.main()
