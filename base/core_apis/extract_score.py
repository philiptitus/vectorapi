import re



def extract_first_number(text):
    """
    Extract the first whole number from a block of text with specific conditions.
    
    Args:
        text (str): The text to extract the number from.

    Returns:
        str: The valid number found in the text based on conditions, or '0' if no valid number is found.
    """
    matches = re.findall(r'\b\d+\b', text)
    
    if not matches:
        return '0'

    first_number = int(matches[0])
    
    if first_number < 10 or first_number > 100:
        if len(matches) > 1:
            second_number = int(matches[1])
            if second_number < 10 or second_number > 100:
                return '0'
            else:
                return str(second_number)
        else:
            return '0'
    
    return str(first_number)
