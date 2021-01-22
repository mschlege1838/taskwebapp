
function DateTimeField(dateInput, timeInput, clearButton, midnightButton, eobButton, eodButton) {
    'use strict';
    
    this.dateInput = dateInput;
    this.timeInput = timeInput;
    this.clearButton = clearButton;
    this.midnightButton = midnightButton;
    this.eobButton = eobButton;
    this.eodButton = eodButton;
}

DateTimeField.initAll = function () {
    'use strict';
    
    for (const field of document.getElementsByClassName('datetime-field')) {
        new DateTimeField(field.querySelector('.date-input'), field.querySelector('.time-input'), field.querySelector('.clear-button'),
                field.querySelector('.midnight-button'), field.querySelector('.eob-button'), field.querySelector('.eod-button')).init();
    }
};

DateTimeField.prototype.init = function () {
    'use strict';
    
    this.clearButton.addEventListener('click', this, false);
    this.midnightButton.addEventListener('click', this, false);
    this.eobButton.addEventListener('click', this, false);
    this.eodButton.addEventListener('click', this, false);
};

DateTimeField.prototype.handleEvent = function (event) {
    'use strict';
    
    const timeInput = this.timeInput;
    
    switch (event.target) {
        case this.clearButton:
            timeInput.value = this.dateInput.value = '';
            break;
        case this.midnightButton:
            timeInput.value = '00:00';
            break;
        case this.eobButton:
            timeInput.value = '17:00';
            break;
        case this.eodButton:
            timeInput.value = '23:59';
            break;
    }
};