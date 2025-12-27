/**
 * Универсальная функция для сортировки таблиц
 * Добавляет возможность сортировки по клику на заголовок столбца
 */

(function() {
    'use strict';

    /**
     * Инициализация сортировки для всех таблиц с классом 'sortable'
     */
    function initTableSort() {
        const tables = document.querySelectorAll('table.sortable');
        
        tables.forEach(table => {
            makeTableSortable(table);
        });
    }

    /**
     * Делает таблицу сортируемой
     * @param {HTMLTableElement} table - Таблица для обработки
     */
    function makeTableSortable(table) {
        const headers = table.querySelectorAll('thead th');
        
        headers.forEach((header, index) => {
            // Пропускаем столбцы с классом 'no-sort'
            if (header.classList.contains('no-sort')) {
                return;
            }

            // Добавляем стили для кликабельности
            header.style.cursor = 'pointer';
            header.style.userSelect = 'none';
            header.style.position = 'relative';
            header.style.paddingRight = '20px';
            
            // Добавляем индикатор сортировки
            const sortIndicator = document.createElement('span');
            sortIndicator.className = 'sort-indicator';
            sortIndicator.innerHTML = ' <i class="bi bi-arrow-down-up"></i>';
            sortIndicator.style.position = 'absolute';
            sortIndicator.style.right = '5px';
            sortIndicator.style.opacity = '0.3';
            header.appendChild(sortIndicator);

            // Добавляем обработчик клика
            header.addEventListener('click', () => {
                sortTable(table, index, header);
            });
        });
    }

    /**
     * Сортирует таблицу по указанному столбцу
     * @param {HTMLTableElement} table - Таблица для сортировки
     * @param {number} columnIndex - Индекс столбца
     * @param {HTMLElement} header - Заголовок столбца
     */
    function sortTable(table, columnIndex, header) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Определяем текущее направление сортировки
        const currentDirection = header.dataset.sortDirection || 'none';
        let newDirection = 'asc';
        
        if (currentDirection === 'asc') {
            newDirection = 'desc';
        } else if (currentDirection === 'desc') {
            newDirection = 'asc';
        }

        // Сбрасываем индикаторы на всех заголовках
        table.querySelectorAll('thead th').forEach(th => {
            th.dataset.sortDirection = 'none';
            const indicator = th.querySelector('.sort-indicator');
            if (indicator) {
                indicator.innerHTML = ' <i class="bi bi-arrow-down-up"></i>';
                indicator.style.opacity = '0.3';
            }
        });

        // Устанавливаем новое направление
        header.dataset.sortDirection = newDirection;
        const indicator = header.querySelector('.sort-indicator');
        if (indicator) {
            if (newDirection === 'asc') {
                indicator.innerHTML = ' <i class="bi bi-arrow-up"></i>';
            } else {
                indicator.innerHTML = ' <i class="bi bi-arrow-down"></i>';
            }
            indicator.style.opacity = '1';
        }

        // Сортируем строки
        rows.sort((rowA, rowB) => {
            const cellA = rowA.cells[columnIndex];
            const cellB = rowB.cells[columnIndex];
            
            if (!cellA || !cellB) return 0;

            const valueA = getCellValue(cellA);
            const valueB = getCellValue(cellB);

            let comparison = 0;

            // Определяем тип данных и сравниваем
            if (isDate(valueA) && isDate(valueB)) {
                comparison = compareDates(valueA, valueB);
            } else if (isNumber(valueA) && isNumber(valueB)) {
                comparison = parseFloat(valueA) - parseFloat(valueB);
            } else {
                comparison = valueA.localeCompare(valueB, 'ru', { numeric: true, sensitivity: 'base' });
            }

            return newDirection === 'asc' ? comparison : -comparison;
        });

        // Переставляем строки в таблице
        rows.forEach(row => tbody.appendChild(row));

        // Анимация
        tbody.style.opacity = '0.7';
        setTimeout(() => {
            tbody.style.transition = 'opacity 0.3s';
            tbody.style.opacity = '1';
        }, 50);
    }

    /**
     * Извлекает значение из ячейки таблицы
     * @param {HTMLTableCellElement} cell - Ячейка таблицы
     * @returns {string} - Текстовое значение ячейки
     */
    function getCellValue(cell) {
        // Проверяем наличие атрибута data-sort-value для кастомной сортировки
        if (cell.dataset.sortValue) {
            return cell.dataset.sortValue;
        }

        // Извлекаем текст из ссылок
        const link = cell.querySelector('a');
        if (link) {
            return link.textContent.trim();
        }

        // Извлекаем текст из badge/span
        const badge = cell.querySelector('.badge, span');
        if (badge && badge.textContent.trim()) {
            return badge.textContent.trim();
        }

        return cell.textContent.trim();
    }

    /**
     * Проверяет, является ли строка датой
     * @param {string} value - Значение для проверки
     * @returns {boolean}
     */
    function isDate(value) {
        // Проверяем форматы: dd.mm.yyyy, yyyy-mm-dd
        const datePatterns = [
            /^\d{2}\.\d{2}\.\d{4}$/,  // dd.mm.yyyy
            /^\d{4}-\d{2}-\d{2}$/      // yyyy-mm-dd
        ];
        
        return datePatterns.some(pattern => pattern.test(value));
    }

    /**
     * Сравнивает две даты
     * @param {string} dateA - Первая дата
     * @param {string} dateB - Вторая дата
     * @returns {number}
     */
    function compareDates(dateA, dateB) {
        const parseDate = (dateStr) => {
            // Формат dd.mm.yyyy
            if (dateStr.includes('.')) {
                const [day, month, year] = dateStr.split('.').map(Number);
                return new Date(year, month - 1, day);
            }
            // Формат yyyy-mm-dd
            return new Date(dateStr);
        };

        return parseDate(dateA) - parseDate(dateB);
    }

    /**
     * Проверяет, является ли строка числом
     * @param {string} value - Значение для проверки
     * @returns {boolean}
     */
    function isNumber(value) {
        return !isNaN(parseFloat(value)) && isFinite(value);
    }

    // Инициализация при загрузке страницы
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTableSort);
    } else {
        initTableSort();
    }

    // Экспортируем функцию для ручной инициализации
    window.initTableSort = initTableSort;
})();
