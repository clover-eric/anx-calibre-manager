import { fetch_with_token } from './utils.js';

export function setupCompletions(form) {
    form.querySelectorAll('input[data-completion-field]').forEach(input => {
        let currentFocus;
        
        input.addEventListener('input', function(e) {
            const field = this.dataset.completionField;
            let val = this.value;
            closeAllLists();
            if (!val) { return false; }
            currentFocus = -1;

            const list = document.createElement('div');
            list.setAttribute('id', this.id + 'autocomplete-list');
            list.setAttribute('class', 'autocomplete-items');
            this.parentNode.appendChild(list);

            let query = val;
            if (field === 'authors' || field === 'tags') {
                const parts = val.split(',');
                query = parts[parts.length - 1].trim();
            }

            if (query.length < 1) return;

            fetch_with_token(`/api/calibre/completions?field=${encodeURIComponent(field)}&query=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(items => {
                    items.forEach(item => {
                        const itemDiv = document.createElement('div');
                        itemDiv.innerHTML = "<strong>" + item.substr(0, query.length) + "</strong>";
                        itemDiv.innerHTML += item.substr(query.length);
                        itemDiv.innerHTML += "<input type='hidden' value='" + item + "'>";
                        
                        itemDiv.addEventListener('click', function(e) {
                            let newValue = this.getElementsByTagName('input')[0].value;
                            if (field === 'authors' || field === 'tags') {
                                const parts = val.split(',');
                                parts[parts.length - 1] = newValue;
                                input.value = parts.join(', ') + ', ';
                            } else {
                                input.value = newValue;
                            }
                            closeAllLists();
                        });
                        list.appendChild(itemDiv);
                    });
                });
        });

        input.addEventListener('keydown', function(e) {
            let x = document.getElementById(this.id + 'autocomplete-list');
            if (x) x = x.getElementsByTagName('div');
            if (e.keyCode == 40) { // down
                currentFocus++;
                addActive(x);
            } else if (e.keyCode == 38) { // up
                currentFocus--;
                addActive(x);
            } else if (e.keyCode == 13) { // enter
                e.preventDefault();
                if (currentFocus > -1) {
                    if (x) x[currentFocus].click();
                }
            }
        });

        function addActive(x) {
            if (!x) return false;
            removeActive(x);
            if (currentFocus >= x.length) currentFocus = 0;
            if (currentFocus < 0) currentFocus = (x.length - 1);
            x[currentFocus].classList.add('autocomplete-active');
        }

        function removeActive(x) {
            for (let i = 0; i < x.length; i++) {
                x[i].classList.remove('autocomplete-active');
            }
        }

        function closeAllLists(elmnt) {
            const items = document.getElementsByClassName('autocomplete-items');
            for (let i = 0; i < items.length; i++) {
                if (elmnt != items[i] && elmnt != input) {
                    items[i].parentNode.removeChild(items[i]);
                }
            }
        }
        
        document.addEventListener('click', function (e) {
            closeAllLists(e.target);
        });
    });
}