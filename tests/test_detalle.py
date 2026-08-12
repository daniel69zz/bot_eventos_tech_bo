"""Lectura de la página del evento: __NEXT_DATA__ (Luma) y JSON-LD (Eventbrite/Meetup)."""
import json
import unittest
from unittest import mock

from fuentes import detalle

HTML_LUMA = """
<html><body>
<script id="__NEXT_DATA__" type="application/json">%s</script>
</body></html>
""" % json.dumps({"props": {"pageProps": {"initialData": {"data": {
    "event": {
        "name": "Meetup de IA",
        "start_at": "2026-02-11T16:30:00.000Z",   # 12:30 en Bolivia (UTC-4)
        "timezone": "America/La_Paz",
        "geo_address_info": {"city": "La Paz", "address": "Calle 21, Calacoto"},
    },
    "description_mirror": {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Charla sobre LLMs."}]}]},
}}}}})

HTML_JSONLD = """
<html><head>
<script type="application/ld+json">%s</script>
</head></html>
""" % json.dumps({
    "@context": "https://schema.org",
    "@type": "Event",
    "name": "Conferencia de Ciberseguridad",
    "startDate": "2026-09-15T19:00:00-04:00",
    "description": "<p>Charla <b>abierta</b> al público.</p>",
    "location": {"@type": "Place", "name": "Auditorio UMSA",
                 "address": {"@type": "PostalAddress", "streetAddress": "Av. Villazón",
                             "addressLocality": "La Paz", "addressCountry": "BO"}},
})


class TestFechaDeIso(unittest.TestCase):
    def test_formatos_habituales(self):
        casos = {
            "2026-09-15T19:00:00-04:00": "2026-09-15",
            "2026-09-15T19:00:00Z": "2026-09-15",
            "2026-09-15T19:00": "2026-09-15",
            "2026-09-15": "2026-09-15",
            "2026-09-15 19:00 (hora de Bolivia)": "2026-09-15",
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(detalle._fecha_de_iso(entrada), esperado)

    def test_valores_invalidos(self):
        for valor in ("", None, "proximamente", 123):
            with self.subTest(valor=valor):
                self.assertIsNone(detalle._fecha_de_iso(valor))

    def test_no_desplaza_el_dia_por_la_zona_horaria(self):
        # 19:00 en Bolivia es 23:00 UTC del MISMO día: no debe pasar al siguiente.
        self.assertEqual(detalle._fecha_de_iso("2026-09-15T19:00:00-04:00"), "2026-09-15")


class TestCamposLuma(unittest.TestCase):
    def test_extrae_fecha_local_ciudad_y_descripcion(self):
        campos = detalle._campos_luma(HTML_LUMA)
        self.assertEqual(campos["fecha"], "2026-02-11")
        self.assertEqual(campos["ciudad"], "La Paz")
        self.assertEqual(campos["nombre"], "Meetup de IA")
        self.assertIn("Calacoto", campos["lugar"])
        self.assertEqual(campos["descripcion"], "Charla sobre LLMs.")

    def test_html_sin_next_data(self):
        self.assertIsNone(detalle._campos_luma("<html>nada</html>"))

    def test_next_data_corrupto(self):
        html = '<script id="__NEXT_DATA__">{roto</script>'
        self.assertIsNone(detalle._campos_luma(html))


class TestCamposJsonLd(unittest.TestCase):
    def test_evento_simple(self):
        campos = detalle._campos_jsonld(HTML_JSONLD)
        self.assertEqual(campos["fecha"], "2026-09-15")
        self.assertEqual(campos["ciudad"], "La Paz")
        self.assertEqual(campos["nombre"], "Conferencia de Ciberseguridad")
        self.assertIn("Auditorio UMSA", campos["lugar"])
        self.assertEqual(campos["descripcion"], "Charla abierta al público.")  # sin HTML

    def test_evento_dentro_de_una_lista(self):
        html = '<script type="application/ld+json">%s</script>' % json.dumps(
            [{"@type": "WebPage"}, {"@type": "Event", "name": "X", "startDate": "2026-05-01"}])
        self.assertEqual(detalle._campos_jsonld(html)["fecha"], "2026-05-01")

    def test_evento_dentro_de_grafo(self):
        html = '<script type="application/ld+json">%s</script>' % json.dumps(
            {"@graph": [{"@type": "Organization"},
                        {"@type": ["Event", "SocialEvent"], "name": "Y", "startDate": "2026-05-02"}]})
        self.assertEqual(detalle._campos_jsonld(html)["fecha"], "2026-05-02")

    def test_ignora_bloques_rotos_y_sigue_buscando(self):
        html = ('<script type="application/ld+json">{roto</script>' + HTML_JSONLD)
        self.assertEqual(detalle._campos_jsonld(html)["ciudad"], "La Paz")

    def test_sin_jsonld(self):
        self.assertIsNone(detalle._campos_jsonld("<html>nada</html>"))

    def test_jsonld_sin_evento(self):
        html = '<script type="application/ld+json">{"@type": "Organization"}</script>'
        self.assertIsNone(detalle._campos_jsonld(html))


class TestEnriquecer(unittest.TestCase):
    def _con_html(self, html):
        respuesta = mock.Mock()
        respuesta.text = html
        return mock.patch.object(detalle.red, "pedir", return_value=respuesta)

    def test_meetup_usa_jsonld(self):
        candidato = {"url": "https://www.meetup.com/g/events/1/", "fuente": "Meetup",
                     "titulo": "t", "snippet": "pobre"}
        with self._con_html(HTML_JSONLD):
            detalle.enriquecer(candidato)
        self.assertEqual(candidato["fecha_oficial"], "2026-09-15")
        self.assertEqual(candidato["ciudad_oficial"], "La Paz")
        self.assertIn("Fecha: 2026-09-15", candidato["snippet"])

    def test_luma_usa_next_data(self):
        candidato = {"url": "https://lu.ma/abc", "fuente": "Luma", "titulo": "t", "snippet": ""}
        with self._con_html(HTML_LUMA):
            detalle.enriquecer(candidato)
        self.assertEqual(candidato["fecha_oficial"], "2026-02-11")

    def test_error_de_red_deja_el_candidato_igual(self):
        candidato = {"url": "https://lu.ma/abc", "fuente": "Luma", "titulo": "t", "snippet": "s"}
        with mock.patch.object(detalle.red, "pedir", side_effect=RuntimeError("timeout")):
            detalle.enriquecer(candidato)
        self.assertEqual(candidato, {"url": "https://lu.ma/abc", "fuente": "Luma",
                                     "titulo": "t", "snippet": "s"})

    def test_solo_toca_las_fuentes_con_pagina_propia(self):
        candidatos = [{"url": "https://x.bo", "fuente": "Facebook", "titulo": "t", "snippet": ""},
                      {"url": "https://lu.ma/a", "fuente": "Luma", "titulo": "t", "snippet": ""}]
        with self._con_html(HTML_LUMA) as pedir:
            detalle.enriquecer_lista(candidatos)
        self.assertEqual(pedir.call_count, 1)
        self.assertNotIn("fecha_oficial", candidatos[0])


if __name__ == "__main__":
    unittest.main()
