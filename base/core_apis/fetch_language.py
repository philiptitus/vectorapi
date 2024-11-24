from base.core_apis.data.languages import programming_languages

def extract_language_from_answer(answer):
    # Normalize the case to make the check case-insensitive
    words = answer.replace('```', '').replace('**', '').lower().split()
    lower_case_languages = [lang.lower() for lang in programming_languages]
    for word in words:
        if word in lower_case_languages:
            return programming_languages[lower_case_languages.index(word)]
    return "NONE"