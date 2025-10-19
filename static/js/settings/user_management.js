// ==================== User Management (Admin Only) ====================
// This file handles user management functionality for administrators

/**
 * Fetch and display all users
 */
async function fetchUsers() {
    const response = await fetch('/api/users');
    const users = await response.json();
    const tbody = document.querySelector('#userTable tbody');
    tbody.innerHTML = '';
    users.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${user.role}</td>
            <td>
                <button class="button-small" onclick="editUser(${user.id}, '${user.username}', '${user.role}')">${t.edit}</button>
                <button class="button-danger button-small" onclick="deleteUser(${user.id})">${t.delete}</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

/**
 * Edit a user - populate the form with user data
 * @param {number} id - User ID
 * @param {string} username - Username
 * @param {string} role - User role
 */
window.editUser = function(id, username, role) {
    document.getElementById('formTitle').textContent = t.edit;
    document.getElementById('user_id').value = id;
    document.getElementById('username').value = username;
    document.getElementById('role').value = role;
    window.scrollTo(0, 0);
}

/**
 * Reset the user form to add mode
 */
window.resetUserForm = function() {
    document.getElementById('formTitle').textContent = t.add;
    document.getElementById('userForm').reset();
    document.getElementById('user_id').value = '';
}

/**
 * Handle user form submission (add or edit)
 * @param {Event} event - The form submission event
 */
window.handleUserFormSubmit = async function(event) {
    event.preventDefault();
    const form = event.target;
    const userId = form.user_id.value;
    const url = '/api/users';
    const method = userId ? 'PUT' : 'POST';

    const data = {
        username: form.username.value,
        password: form.password.value,
        role: form.role.value
    };
    
    if (userId) {
        data.user_id = userId;
    }

    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        location.reload();
    }
}

/**
 * Delete a user
 * @param {number} userId - The ID of the user to delete
 */
window.deleteUser = async function(userId) {
    if (!confirm(t.confirmDeleteUser)) return;

    const response = await fetch(`/api/users`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    });
    
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        location.reload();
    }
}