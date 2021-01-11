

/**
 * @callback onMatches
 * @param {string[]} matches Results matching the currently entered text.
 */


////////////////////////////////
/**
 * @callback fetchMatches
 * @param {string} current Current entered text.
 * @param {onMatches} onMatches Callback to execute when fetch is successful.
 */

////////////////////////////////

/**
 * @typedef AutocompleteMatcher
 */
/**
 * {@link fetchMatches}
 *
 * @function AutocompleteInput#fetchMatches
 * @param {string} current Current entered text.
 * @param {onMatches} onMatches Callback to execute when fetch is successful.
 */

////////////////////////////////




//// Features to implement:

// Scroll with selection when using up/down arrows
function AutocompleteInput(input, matcher, options) {
    'use strict';
    
    var autocompleteList, _this, autocompleteElement;
    
    this.input = input;
    this.matcher = matcher;
    
    if (options) {
        if (options.matchDelay) {
            this.matchDelay = options.matchDelay;
        }
        if (!options.preventDefaultOnTab) {
            this.preventDefaultOnTab = options.preventDefaultOnTab;
        }
        if (typeof options.ignoreCase !== 'undefined') {
            this.ignoreCase = options.ignoreCase;
        }
        if (options.stopPropagationOnControl) {
            this.stopPropagationOnControl = options.stopPropagationOnControl;
        }
    }
    
    
    this.autocompleteElement = autocompleteElement = document.createElement('div');
    autocompleteElement.className = AutocompleteInput.AUTO_COMPLETE_ELEMENT_CLASS;
    
    autocompleteList = document.createElement('ul');
    autocompleteList.className = AutocompleteInput.AUTO_COMPLETE_LIST_CLASS;
    autocompleteElement.appendChild(autocompleteList);
    
    _this = this;
    this.onMatchesCallback = function (matches) {
        _this.processMatches(matches);
    };
}



AutocompleteInput.AUTO_COMPLETE_ELEMENT_CLASS = 'auto-complete-box';
AutocompleteInput.AUTO_COMPLETE_LIST_CLASS = 'auto-complete-list';
AutocompleteInput.MATCH_SUBSTRING_CLASS_NAME = 'auto-complete-substring';
AutocompleteInput.MATCH_ITEM_CLASS_NAME = 'auto-complete-match-item';
AutocompleteInput.AUTO_COMPLETE_BOX_ACTIVE_CLASS_NAME = 'auto-complete-active';
AutocompleteInput.HIGHLIGHTED_CLASS_NAME = 'highlighted';


AutocompleteInput.setMatchRange = function (matchElement, compareValue, matchText, ignoreCase) {
    'use strict';
    
    var matchIndex, matchSpan, endIndex;
    
    matchIndex = ignoreCase ? matchText.toLowerCase().indexOf(compareValue) : matchText.indexOf(compareValue);
    if (matchIndex === -1) {
        return true;
    }
    
    while (matchElement.childNodes.length) {
        matchElement.removeChild(matchElement.childNodes[0]);
    }
    
    
    endIndex = matchIndex + compareValue.length;
    
    
    matchElement.appendChild(document.createTextNode(matchText.substring(0, matchIndex)));
    
    matchSpan = document.createElement('span');
    matchSpan.className = AutocompleteInput.MATCH_SUBSTRING_CLASS_NAME;
    matchSpan.appendChild(document.createTextNode(matchText.substring(matchIndex, endIndex)));
    matchElement.appendChild(matchSpan);
    
    matchElement.appendChild(document.createTextNode(matchText.substring(endIndex)));
};




AutocompleteInput.prototype.timeoutId = 0;
AutocompleteInput.prototype.matchDelay = 100;
AutocompleteInput.prototype.currentMatches = null;
AutocompleteInput.prototype.preventDefaultOnTab = true;
AutocompleteInput.prototype.ignoreCase = true;
AutocompleteInput.prototype.stopPropagationOnControl = true;
AutocompleteInput.prototype.mouseOver = false;


AutocompleteInput.prototype.init = function () {
    'use strict';
    
    var input;
    
    input = this.input;
    this.input.addEventListener('keyup', this, false);
    this.input.addEventListener('keydown', this, false);
    this.input.addEventListener('blur', this, false);
    input.setAttribute('autocomplete', 'off');
    
    document.getElementsByTagName('body')[0].appendChild(this.autocompleteElement);
    
    this.autocompleteElement.addEventListener('mouseenter', this, false);
    this.autocompleteElement.addEventListener('mouseleave', this, false);
};

AutocompleteInput.prototype.dispose = function () {
    'use strict';
    
    var currentMatches, i;
    
    this.input.removeEventListener('keyup', this, false);
    this.input.removeEventListener('keydown', this, false);
    
    currentMatches = this.currentMatches;
    for (i = 0; i < currentMatches.length; ++i) {
        currentMatches[i].removeEventListener('click', this, false);
    }
    this.currentMatches = null;
    
    
    this.autocompleteElement.removeEventListener('mouseenter', this, false);
    this.autocompleteElement.removeEventListener('mouseleave', this, false);
    document.getElementsByTagName('body')[0].removeChild(this.autocompleteElement);
    
    delete this.onMatchesCallback;
};


AutocompleteInput.prototype.handleEvent = function (event) {
    'use strict';
    
    var target, key, keyCode, isTab, highlightedItem;
    
    // TODO: NON-IE8
    target = event.target;
    
    if (target === this.input) {
        switch (event.type) {
            case 'keydown':
                if (!this.isOpen()) {
                    return;
                }
                
                key = event.key;
                keyCode = event.keyCode;
                if (key === 'ArrowDown' || keyCode === 0x28) {
                    this.moveSelection();
                    return;
                }
                
                if (key === 'ArrowUp' || keyCode === 0x26) {
                    this.moveSelection(true);
                    return;
                }
                
                isTab = key === 'Tab' || keyCode === 0x09;
                if (isTab || key === 'Enter' || keyCode === 0x0d) {
                    if (!isTab || this.preventDefaultOnTab) {
                        event.preventDefault();
                    }
                    if (this.stopPropagationOnControl) {
                        event.stopImmediatePropagation();
                    }
                    highlightedItem = this.autocompleteElement.getElementsByClassName(AutocompleteInput.HIGHLIGHTED_CLASS_NAME)[0]
                    if (highlightedItem) {
                        this.updateInput(highlightedItem);
                    }
                    return;
                }
                break;
            case 'keyup':
                key = event.key;
                keyCode = event.keyCode;
                if (!(key === 'ArrowDown' || keyCode === 0x28 || key === 'ArrowUp' || keyCode === 0x26 || key === 'Tab' || 
                        keyCode === 0x09 || isTab || key === 'Enter' || keyCode === 0x0d)) {
                    this.initMatch();
                }
                break;
            case 'blur':
                if (!this.mouseOver) {
                    this.closeBox();
                }
                break;
        }
    }
    
    else if (target === this.autocompleteElement) {
        switch (event.type) {
            case 'mouseenter':
                this.mouseOver = true;
                break;
            case 'mouseleave':
                this.mouseOver = false;
                break;
        }
    }
    
    // TODO: NON-IE8
    else if (target.classList.contains(AutocompleteInput.MATCH_ITEM_CLASS_NAME)) {
        switch (event.type) {
            case 'click':
                this.updateInput(target);
                break;
            case 'mouseenter':
                this.scrollOver(target);
                break;
        }
        
    }
};


AutocompleteInput.prototype.initMatch = function () {
    'use strict';
    
    var currentTimeout, _this;
    
    _this = this;
    currentTimeout = this.timeoutId;
    
    if (currentTimeout) {
        clearTimeout(currentTimeout);
    }
    
    if (!this.input.value) {
        this.closeBox();
        return;
    }
    
    this.timeoutId = setTimeout(function () {
        _this.fetchMatch();
    }, this.matchDelay)
};


AutocompleteInput.prototype.fetchMatch = function () {
    'use strict';
    
    var matcher, currentValue, onMatchesCallback;
    
    currentValue = this.input.value;
    matcher = this.matcher;
    onMatchesCallback = this.onMatchesCallback;
    
    if (typeof matcher.fetchMatches === 'function') {
        matcher.fetchMatches(currentValue, onMatchesCallback);
    } else {
        matcher(currentValue, onMatchesCallback);
    }
};


AutocompleteInput.prototype.processMatches = function (matches) {
    'use strict';
    
    var autocompleteElement, autocompleteList, i, currentMatches, matchIndex, input, currentValue, 
        match, matchElement, offsetCoordinates, ignoreCase, compareValue;
    
    
    // NOthing to process if no matches returned.
    if (!matches || !matches.length) {
        this.closeBox();
        return;
    }
    
    // Setup.
    autocompleteElement = this.autocompleteElement;
    autocompleteList = autocompleteElement.getElementsByClassName(AutocompleteInput.AUTO_COMPLETE_LIST_CLASS)[0];
    input = this.input;
    ignoreCase = this.ignoreCase;
    
    currentValue = input.value;
    compareValue = ignoreCase ? currentValue.toLowerCase() : currentValue;
    
    // Process current list.
    currentMatches = autocompleteList.querySelectorAll('[data-match-word]');
    for (i = 0; i < currentMatches.length; ++i) {
        matchElement = currentMatches[i];
        matchIndex = matches.indexOf(matchElement.getAttribute('data-match-word'));
        if (matchIndex === -1) {
            this.removeMatch(matchElement);
        } else {
            if (AutocompleteInput.setMatchRange(matchElement, compareValue, matches[matchIndex], ignoreCase)) {
                this.removeMatch(matchElement);
            }
            matches.splice(matchIndex, 1);
        }
    }
    
    // Add new items, if any.
    for (i = 0; i < matches.length; ++i) {
        match = matches[i];
        
        matchElement = document.createElement('li');
        if (AutocompleteInput.setMatchRange(matchElement, compareValue, match, ignoreCase)) {
            continue;
        }
        matchElement.setAttribute('data-match-word', match);
        matchElement.className = AutocompleteInput.MATCH_ITEM_CLASS_NAME;
        matchElement.addEventListener('click', this, false);
        matchElement.addEventListener('mouseenter', this, false);
        
        autocompleteList.appendChild(matchElement);
    }
    
    // Not likely, but just in case input value has been changed since match fetch initiated...
    if (!autocompleteList.getElementsByClassName(AutocompleteInput.MATCH_ITEM_CLASS_NAME).length) {
        console.warn('No matching items for current value: ' + currentValue);
        return;
    }
    
    
    // Position box.
    offsetCoordinates = OffsetCoordinates.getOffset(input);
    autocompleteElement.style.left = offsetCoordinates.x + 'px';
    autocompleteElement.style.top = (offsetCoordinates.y + input.offsetHeight) + 'px';
    autocompleteElement.style.minWidth = input.offsetWidth + 'px';
    // TODO: NON-IE8
    autocompleteElement.classList.add(AutocompleteInput.AUTO_COMPLETE_BOX_ACTIVE_CLASS_NAME);
    
    
    // Select first item if none selected.
    if (!autocompleteList.getElementsByClassName(AutocompleteInput.HIGHLIGHTED_CLASS_NAME).length) {
        this.moveSelection();
    }
    
};

AutocompleteInput.prototype.moveSelection = function (up) {
    'use strict';
    
    var autocompleteItems, i, targetIndex, item;
    
    autocompleteItems = this.autocompleteElement.getElementsByClassName(AutocompleteInput.MATCH_ITEM_CLASS_NAME);
    
    // Calculate target based upon current highlighted item.
    targetIndex = up ? autocompleteItems.length : -1;
    for (i = 0; i < autocompleteItems.length; ++i) {
        item = autocompleteItems[i];
        if (item.classList.contains(AutocompleteInput.HIGHLIGHTED_CLASS_NAME)) {
            item.classList.remove(AutocompleteInput.HIGHLIGHTED_CLASS_NAME);
            targetIndex = i;
            break;
        }
    }
    
    // Increment/decrement appropriately.
    if (up) {
        targetIndex -= 1;
    } else {
        targetIndex += 1;
    }
    
    // Overflow handling.
    if (targetIndex < 0) {
        targetIndex = autocompleteItems.length - 1;
    } else if (targetIndex >= autocompleteItems.length) {
        targetIndex = 0;
    }
    
    // Highlight new target.
    autocompleteItems[targetIndex].classList.add(AutocompleteInput.HIGHLIGHTED_CLASS_NAME);
};

AutocompleteInput.prototype.scrollOver = function (target) {
    'use strict';
    
    var autocompleteItems, i, item;
    
    autocompleteItems = this.autocompleteElement.getElementsByClassName(AutocompleteInput.MATCH_ITEM_CLASS_NAME);
    
    for (i = 0; i < autocompleteItems.length; ++i) {
        item = autocompleteItems[i];
        if (item === target) {
            item.classList.add(AutocompleteInput.HIGHLIGHTED_CLASS_NAME);
        } else {
            item.classList.remove(AutocompleteInput.HIGHLIGHTED_CLASS_NAME);
        }
    }
    
};

AutocompleteInput.prototype.closeBox = function () {
    'use strict';

    this.autocompleteElement.classList.remove(AutocompleteInput.AUTO_COMPLETE_BOX_ACTIVE_CLASS_NAME);
};

AutocompleteInput.prototype.isOpen = function () {
    'use strict';
    
    return this.autocompleteElement.classList.contains(AutocompleteInput.AUTO_COMPLETE_BOX_ACTIVE_CLASS_NAME);
};

AutocompleteInput.prototype.updateInput = function (item) {
    'use strict';
    
    // TODO: NON-IE8
    this.input.value = item.textContent;
    this.closeBox();
};


AutocompleteInput.prototype.removeMatch = function (matchElement) {
    'use strict';
    
    matchElement.removeEventListener('click', this, false);
    matchElement.removeEventListener('mouseenter', this, false);
    matchElement.parentNode.removeChild(matchElement);
};