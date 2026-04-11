document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('[data-skills-form]');
  if (!form) return;

  const shell = form.querySelector('[data-tag-input]');
  const list = form.querySelector('[data-tag-list]');
  const input = form.querySelector('[data-tag-text]');
  const hidden = form.querySelector('input[name="skills_json"]');

  let tags = [];
  try {
    tags = JSON.parse(hidden.value || '[]');
    if (!Array.isArray(tags)) tags = [];
  } catch (error) {
    tags = [];
  }

  const sync = () => {
    hidden.value = JSON.stringify(tags);
    list.innerHTML = '';
    tags.forEach((tag, index) => {
      const chip = document.createElement('span');
      chip.className = 'tag-chip';
      chip.innerHTML = `<span>${tag}</span><button type="button" aria-label="Remove ${tag}" data-index="${index}">&times;</button>`;
      list.appendChild(chip);
    });
  };

  const addTag = (value) => {
    const clean = value.trim();
    if (!clean) return;
    if (tags.some((tag) => tag.toLowerCase() === clean.toLowerCase())) return;
    tags.push(clean);
    sync();
  };

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      addTag(input.value);
      input.value = '';
    }
    if (event.key === 'Backspace' && !input.value && tags.length) {
      tags.pop();
      sync();
    }
  });

  input.addEventListener('blur', () => {
    if (input.value.trim()) {
      addTag(input.value);
      input.value = '';
    }
  });

  shell.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-index]');
    if (!button) {
      input.focus();
      return;
    }
    tags.splice(Number(button.dataset.index), 1);
    sync();
    input.focus();
  });

  sync();
});
