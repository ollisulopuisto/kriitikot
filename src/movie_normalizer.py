"""
Elokuvien nimien normalisointi fuzzy matchingilla.

Yhdistää samaa elokuvaa tarkoittavat eri kirjoitusasut:
- "Sorry, Baby" vs "Sorry, baby"
- "Springsteen: Deliver Me from Nowhere" vs "Springsteen: Deliver Me From Nowhere"
"""

import re
from typing import Optional
from difflib import SequenceMatcher


def normalize_movie_title(title: str) -> str:
    """
    Normalisoi elokuvan nimen vertailua varten.
    
    Poistaa välimerkit, muuttaa pieniksi kirjaimiksi ja normalisoi välilyönnit.
    
    Args:
        title: Alkuperäinen elokuvan nimi
        
    Returns:
        Normalisoitu nimi
    """
    if not title:
        return ""
    
    # Pienillä kirjaimilla
    normalized = title.lower()
    
    # Poista välimerkit (säilytä välilyönnit)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Normalisoi välilyönnit (useampi välilyönti -> yksi)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Poista tyhjät alusta ja lopusta
    normalized = normalized.strip()
    
    return normalized


def similarity_ratio(title1: str, title2: str) -> float:
    """
    Laskee kahden elokuvan nimen samankaltaisuuden (0.0 - 1.0).
    
    Käyttää SequenceMatcheria normalisoiduille nimille.
    
    Args:
        title1: Ensimmäinen elokuvan nimi
        title2: Toinen elokuvan nimi
        
    Returns:
        Samankaltaisuus 0.0 (täysin erilaiset) - 1.0 (identtiset)
    """
    norm1 = normalize_movie_title(title1)
    norm2 = normalize_movie_title(title2)
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def are_same_movie(title1: str, title2: str, threshold: float = 0.9) -> bool:
    """
    Tarkistaa ovatko kaksi nimeä todennäköisesti sama elokuva.
    
    Args:
        title1: Ensimmäinen elokuvan nimi
        title2: Toinen elokuvan nimi
        threshold: Minimitarkkuus (0.0-1.0), oletus 0.9 (90%)
        
    Returns:
        True jos nimet ovat riittävän samankaltaiset
    
    Examples:
        >>> are_same_movie("Sorry, Baby", "Sorry, baby")
        True
        >>> are_same_movie("Springsteen: Deliver Me from Nowhere", 
        ...                "Springsteen: Deliver Me From Nowhere")
        True
        >>> are_same_movie("Bugonia", "Exit 8")
        False
    """
    return similarity_ratio(title1, title2) >= threshold


def find_matching_movie(new_title: str, existing_titles: list[str], 
                        threshold: float = 0.9) -> Optional[str]:
    """
    Etsii vastaavan elokuvan nimen olemassa olevista nimistä.
    
    Args:
        new_title: Uusi elokuvan nimi
        existing_titles: Lista olemassa olevista nimistä
        threshold: Minimitarkkuus matchille
        
    Returns:
        Löydetty vastaava nimi tai None jos ei löydy
        
    Example:
        >>> existing = ["Sorry, Baby", "Bugonia", "Exit 8"]
        >>> find_matching_movie("Sorry, baby", existing)
        'Sorry, Baby'
    """
    best_match = None
    best_ratio = 0.0
    
    for existing_title in existing_titles:
        ratio = similarity_ratio(new_title, existing_title)
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = existing_title
    
    return best_match


def get_canonical_title(new_title: str, existing_titles: list[str],
                        threshold: float = 0.9) -> str:
    """
    Palauttaa kanonisen (ensimmäisen) version elokuvan nimestä.
    
    Jos löytyy vastaava olemassa oleva nimi, palautetaan se.
    Muuten palautetaan uusi nimi sellaisenaan.
    
    Args:
        new_title: Uusi elokuvan nimi
        existing_titles: Lista olemassa olevista nimistä
        threshold: Minimitarkkuus matchille
        
    Returns:
        Kanoninen elokuvan nimi (joko olemassa oleva tai uusi)
        
    Example:
        >>> existing = ["Sorry, Baby", "Bugonia"]
        >>> get_canonical_title("Sorry, baby", existing)
        'Sorry, Baby'
        >>> get_canonical_title("Exit 8", existing)
        'Exit 8'
    """
    match = find_matching_movie(new_title, existing_titles, threshold)
    return match if match else new_title
