"""Full publication names for visible abbreviations and accessible labels."""
PUBLICATION_NAMES = {
    'HS': 'Helsingin Sanomat',
    'IS': 'Ilta-Sanomat',
    'TS': 'Turun Sanomat',
    'IL': 'Iltalehti',
    'KSML': 'Keskisuomalainen',
    'SK': 'Suomen Kuvalehti',
    'EPISODI': 'Episodi',
    'MUROPAKETTI': 'Muropaketti',
    'MURO': 'Muropaketti',
    'FILMOHOLIC': 'Film-O-Holic',
    'KULTTUURITOIMITUS': 'Kulttuuritoimitus',
    'KUTO': 'Kulttuuritoimitus',
    'DEMOKRAATTI': 'Demokraatti',
}


def publication_name(code):
    """Preserve unknown codes instead of inventing an expansion."""
    return PUBLICATION_NAMES.get(str(code).upper(), code)


def publication_names(codes):
    return ', '.join(publication_name(code) for code in codes)
