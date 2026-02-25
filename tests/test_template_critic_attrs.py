def test_templates_have_critic_id_attributes():
    """Ensure templates include critic id attributes for JS filtering."""
    # Check index.html for header cells
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        index_content = f.read()
    
    assert 'data-critic-id="{{ critic.id }}"' in index_content, 'Header cells must include data-critic-id attribute in templates/index.html'
    
    # Check _movie_card.html for mobile review items
    with open('templates/_movie_card.html', 'r', encoding='utf-8') as f:
        card_content = f.read()
        
    assert 'data-critic="{{ critic.id }}"' in card_content, 'Mobile review items must use critic id in data-critic in templates/_movie_card.html'
