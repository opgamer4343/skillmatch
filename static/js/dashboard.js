document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-tag-input]').forEach((wrapper) => {
        const list = wrapper.querySelector('.tag-list');
        const input = wrapper.querySelector('.tag-entry');
        const hidden = wrapper.querySelector('input[type="hidden"]');

        let tags = [];
        try {
            const currentValue = hidden.value.trim();
            if (currentValue) {
                tags = JSON.parse(currentValue.replace(/'/g, '"'));
            }
        } catch (error) {
            tags = [];
        }

        const sync = () => {
            hidden.value = JSON.stringify(tags);
            list.innerHTML = '';
            tags.forEach((tag, index) => {
                const chip = document.createElement('span');
                chip.className = 'skill-chip';
                chip.innerHTML = `${tag} <button type="button" data-index="${index}" aria-label="Remove ${tag}">&times;</button>`;
                list.appendChild(chip);
            });
        };

        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ',') {
                event.preventDefault();
                const value = input.value.trim();
                if (!value) return;
                if (!tags.includes(value)) {
                    tags.push(value);
                    sync();
                }
                input.value = '';
            }
        });

        list.addEventListener('click', (event) => {
            const button = event.target.closest('button[data-index]');
            if (!button) return;
            const index = Number(button.dataset.index);
            tags.splice(index, 1);
            sync();
        });

        sync();
    });
});
