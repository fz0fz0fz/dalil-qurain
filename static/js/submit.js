function showFields() {
    const select = document.getElementById('category_id');
    const groups = document.querySelectorAll('.field-group');

    groups.forEach(function (group) {
        group.style.display = 'none';
    });

    const selectedId = select ? select.value : '';
    if (selectedId) {
        const target = document.getElementById('fields-' + selectedId);
        if (target) {
            target.style.display = 'block';
        }
    }
}

document.addEventListener('DOMContentLoaded', showFields);
