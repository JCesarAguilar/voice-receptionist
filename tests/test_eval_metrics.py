import pytest

from scripts.eval_metrics import user_turns, word_error_rate


def test_identical_text_has_zero_errors():
    assert word_error_rate("quiero una consulta", "quiero una consulta") == 0


def test_one_wrong_word_out_of_four_is_25_percent():
    assert word_error_rate("me llamo julio cesar", "me llamo cuyo cesar") == 0.25


def test_accents_case_and_punctuation_do_not_count():
    assert word_error_rate("Sí, César.", "si cesar") == 0


def test_numbers_are_compared_digit_by_digit():
    assert word_error_rate("956 582 267", "9 5 6 5 8 2 2 6 7") == 0


def test_an_extra_digit_counts_as_an_error():
    assert word_error_rate("956582267", "9565822267") == pytest.approx(1 / 9)


def test_only_the_client_lines_are_used():
    transcript = "AI: Hola\nUser: Laboral.\nAI: ¿Qué día?\nUser: El jueves"
    assert user_turns(transcript) == "Laboral. El jueves"
