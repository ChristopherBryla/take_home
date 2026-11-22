from newstracker.relevance import mentions_company


def article(title="", description=""):
    return {"title": title, "description": description}


def test_matches_company_name_in_any_case():
    assert mentions_company(article("Why amazon shares fell"), "Amazon")


def test_matches_uppercase_ticker():
    assert mentions_company(article(description="AMZN rallied on Friday"), "Amazon")


def test_matches_ticker_with_dot():
    assert mentions_company(article("BRK.B hits a record"), "Berkshire Hathaway")


def test_either_alphabet_ticker_matches():
    assert mentions_company(article("GOOGL up 2%"), "Alphabet")
    assert mentions_company(article("GOOG up 2%"), "Alphabet")


def test_ordinary_words_do_not_match_tickers():
    assert not mentions_company(article("Well, that went fine"), "Welltower")
    assert not mentions_company(article("A linear model"), "Linde")
    assert not mentions_company(article("Generate more ideas"), "GE Aerospace")


def test_name_inside_a_longer_word_does_not_match():
    assert not mentions_company(article("Amazonian rainforest fires"), "Amazon")


def test_aliases_match_their_company():
    assert mentions_company(article("Google unveils a new chip"), "Alphabet")
    assert mentions_company(article("Exxon raises its dividend"), "ExxonMobil")
    assert mentions_company(article("Lilly's obesity drug wins approval"), "Eli Lilly")
    assert mentions_company(article("NextEra signs a solar deal"), "NextEra Energy")
    assert not mentions_company(article("Google unveils a new chip"), "Amazon")


def test_google_news_boilerplate_does_not_count_as_alphabet():
    boilerplate = "Canada joins NATO investment fund Quinte NewsSee more headlines & perspectives on Google News"

    assert not mentions_company(article(description=boilerplate), "Alphabet")
    assert mentions_company(article(description=boilerplate + ". Google also said"), "Alphabet")


def test_missing_text_does_not_crash():
    assert not mentions_company({"title": None, "description": None}, "Amazon")
