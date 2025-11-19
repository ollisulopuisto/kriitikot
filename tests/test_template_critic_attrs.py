def test_templates_have_critic_id_attributes():
    """Ensure `templates/index.html` includes data-critic-id on header cells and mobile review items use critic id."""
    path = 'templates/index.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'data-critic-id="{{ critic.id }}"' in content, 'Header cells must include data-critic-id attribute'
    assert 'data-critic="{{ critic.id }}"' in content, 'Mobile review items must use critic id in data-critic'
