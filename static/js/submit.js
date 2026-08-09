function setGroupDisabled(group, disabled) {
    const controls = group.querySelectorAll('input, select, textarea, button');
    controls.forEach(function (control) {
        control.disabled = disabled;
    });
}

function showFields() {
    const select = document.getElementById('category_id');
    const groups = document.querySelectorAll('.field-group');

    groups.forEach(function (group) {
        group.style.display = 'none';
        setGroupDisabled(group, true);
    });

    const selectedId = select ? select.value : '';
    if (selectedId) {
        const target = document.getElementById('fields-' + selectedId);
        if (target) {
            target.style.display = 'block';
            setGroupDisabled(target, false);
        }
    }
}

document.addEventListener('DOMContentLoaded', showFields);
