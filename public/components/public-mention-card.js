/**
 * Public Mention Card — stub renderer for regatta and sailor public pages.
 * Used by: regatta public page (regatta-level mentions), sailor public page (inherited via participation).
 *
 * Facebook handling (guardrails for future work):
 * - Facebook URLs may be stored only at regatta level.
 * - Only Facebook Pages allow engagement; Groups and personal profiles are record-only.
 * - No automated Facebook actions will ever be implemented.
 */

(function () {
  'use strict';

  var template = document.getElementById('public-mention-card-tpl');
  if (!template || !template.content) return;

  /**
   * Render a single mention card (stub: no real data binding).
   * @param {Object} opts - Placeholder options: { id, thumbnailUrl, contentType, title, context, url }
   * @returns {HTMLElement}
   */
  function renderPublicMentionCard(opts) {
    opts = opts || {};
    var clone = document.importNode(template.content, true);
    var card = clone.querySelector('.public-mention-card');
    var thumb = clone.querySelector('.public-mention-card__thumb img');
    var icon = clone.querySelector('.public-mention-card__icon');
    var titleLink = clone.querySelector('.public-mention-card__title a');
    var context = clone.querySelector('.public-mention-card__context');
    var link = clone.querySelector('.public-mention-card__link');

    card.dataset.mentionId = opts.id || '';
    if (opts.thumbnailUrl) {
      thumb.src = opts.thumbnailUrl;
      thumb.alt = opts.title || 'Mention';
    } else {
      thumb.parentElement.style.display = 'none';
    }
    icon.dataset.contentType = opts.contentType || '';
    titleLink.textContent = opts.title || '(Placeholder title)';
    titleLink.href = opts.url || '#';
    context.textContent = opts.context || '(Placeholder context)';
    link.href = opts.url || '#';

    return clone.firstElementChild;
  }

  window.renderPublicMentionCard = renderPublicMentionCard;
})();
