function showFields() {
    var select = document.getElementById('category_id');
    var groups = document.querySelectorAll('.field-group');

    groups.forEach(function (group) {
        group.style.display = 'none';
    });

    var selectedId = select.value;
    if (selectedId) {
        var target = document.getElementById('fields-' + selectedId);
        if (target) {
            target.style.display = 'block';
        }
    }
}

document.addEventListener('DOMContentLoaded', showFields);
