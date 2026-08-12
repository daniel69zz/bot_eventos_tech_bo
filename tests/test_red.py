"""Cliente HTTP: qué se reintenta, qué no, y cuánto se espera."""
import unittest
from unittest import mock

import requests

import red


def _respuesta(codigo, cabeceras=None, cuerpo=None):
    r = mock.Mock()
    r.status_code = codigo
    r.headers = cabeceras or {}
    r.text = "cuerpo"
    r.json.return_value = cuerpo if cuerpo is not None else {}
    return r


class TestPedir(unittest.TestCase):
    def setUp(self):
        dormir = mock.patch.object(red.time, "sleep")
        self.dormir = dormir.start()
        self.addCleanup(dormir.stop)

    def test_exito_a_la_primera(self):
        ok = _respuesta(200)
        with mock.patch.object(red.requests, "request", return_value=ok) as pedido:
            self.assertIs(red.pedir("GET", "https://x.bo"), ok)
        self.assertEqual(pedido.call_count, 1)
        self.dormir.assert_not_called()

    def test_reintenta_429_y_termina_bien(self):
        with mock.patch.object(red.requests, "request",
                               side_effect=[_respuesta(429), _respuesta(200)]) as pedido:
            self.assertEqual(red.pedir("GET", "https://x.bo").status_code, 200)
        self.assertEqual(pedido.call_count, 2)

    def test_respeta_retry_after_de_la_cabecera(self):
        respuestas = [_respuesta(429, {"Retry-After": "7"}), _respuesta(200)]
        with mock.patch.object(red.requests, "request", side_effect=respuestas):
            red.pedir("GET", "https://x.bo")
        self.assertAlmostEqual(self.dormir.call_args[0][0], 7.0)

    def test_respeta_retry_after_de_telegram(self):
        cuerpo = {"ok": False, "parameters": {"retry_after": 12}}
        respuestas = [_respuesta(429, cuerpo=cuerpo), _respuesta(200)]
        with mock.patch.object(red.requests, "request", side_effect=respuestas):
            red.pedir("POST", "https://api.telegram.org")
        self.assertAlmostEqual(self.dormir.call_args[0][0], 12.0)

    def test_no_reintenta_errores_del_cliente(self):
        # Un 401 (clave mal) no mejora reintentando: falla al toque.
        with mock.patch.object(red.requests, "request", return_value=_respuesta(401)) as pedido:
            with self.assertRaises(red.ErrorHttp):
                red.pedir("GET", "https://x.bo")
        self.assertEqual(pedido.call_count, 1)

    def test_agota_intentos_y_lanza(self):
        with mock.patch.object(red.requests, "request", return_value=_respuesta(503)) as pedido:
            with self.assertRaises(red.ErrorHttp):
                red.pedir("GET", "https://x.bo", intentos=3)
        self.assertEqual(pedido.call_count, 3)

    def test_reintenta_timeouts(self):
        efectos = [requests.Timeout("se colgó"), _respuesta(200)]
        with mock.patch.object(red.requests, "request", side_effect=efectos) as pedido:
            self.assertEqual(red.pedir("GET", "https://x.bo").status_code, 200)
        self.assertEqual(pedido.call_count, 2)

    def test_error_de_red_persistente_lanza_errorhttp(self):
        with mock.patch.object(red.requests, "request",
                               side_effect=requests.ConnectionError("sin internet")):
            with self.assertRaises(red.ErrorHttp):
                red.pedir("GET", "https://x.bo", intentos=2)

    def test_backoff_exponencial_creciente(self):
        respuestas = [_respuesta(500), _respuesta(500), _respuesta(200)]
        with mock.patch.object(red.requests, "request", side_effect=respuestas):
            red.pedir("GET", "https://x.bo", intentos=3)
        esperas = [llamada[0][0] for llamada in self.dormir.call_args_list]
        self.assertLess(esperas[0], esperas[1])

    def test_la_espera_nunca_pasa_del_techo(self):
        respuestas = [_respuesta(429, {"Retry-After": "9999"}), _respuesta(200)]
        with mock.patch.object(red.requests, "request", side_effect=respuestas):
            red.pedir("GET", "https://x.bo")
        self.assertLessEqual(self.dormir.call_args[0][0], red.ESPERA_MAX_SEG)


if __name__ == "__main__":
    unittest.main()
