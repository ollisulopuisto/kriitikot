import { beforeEach, describe, expect, it } from 'vitest';
import { minimalHTML, setupDOM } from './test-helper';

describe('Favourite action beside the header review count', () => {
  beforeEach(() => {
    localStorage.clear();
    const html = minimalHTML.replace(
      '<div class="critic-name">Susanna Bono</div>',
      '<div class="critic-name">Susanna Bono</div><div class="critic-bottom-row"><span class="review-count">🎬 7</span></div>'
    );
    setupDOM(html);
  });

  it('places one native button after the count, including headers without a count', () => {
    for (const header of document.querySelectorAll('th.rating-cell')) {
      const row = header.querySelector('.critic-bottom-row');
      const button = row?.querySelector('button.heart-icon');
      expect(button).not.toBeNull();
      expect(button.type).toBe('button');
      expect(header.querySelectorAll('.heart-icon')).toHaveLength(1);
      expect(header.querySelector('.critic-name')).not.toContain(button);
      expect(button.getAttribute('aria-label')).toContain(header.querySelector('.critic-name').textContent.trim());
    }
    const row = document.querySelector('th[data-critic-id="1"] .critic-bottom-row');
    expect(row.lastElementChild).toBe(row.querySelector('.heart-icon'));
    expect(row.firstElementChild.textContent).toBe('🎬 7');
  });

  it('toggles and persists without invoking critic filtering or duplicating buttons', () => {
    const header = document.querySelector('th[data-critic-id="1"]');
    const button = header.querySelector('.heart-icon');
    button.click();
    expect(button.getAttribute('aria-pressed')).toBe('true');
    expect(JSON.parse(localStorage.getItem('kriitikot_favorites'))).toContain('1');
    expect(header.dataset.filtered).not.toBe('true');
    button.click();
    expect(button.getAttribute('aria-pressed')).toBe('false');
    expect(JSON.parse(localStorage.getItem('kriitikot_favorites'))).not.toContain('1');
    expect(header.querySelectorAll('.heart-icon')).toHaveLength(1);
  });
});
