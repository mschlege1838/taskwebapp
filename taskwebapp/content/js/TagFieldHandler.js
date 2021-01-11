


function TagFieldHandler(tagContainer, tagInput, fieldName) {
    'use strict';
    
    this.tagContainer = tagContainer.querySelector('.field-input');
    this.tagInput = tagInput;
    this.fieldName = fieldName;
}

TagFieldHandler.TAG_CLASS_NAME = 'tag';
TagFieldHandler.REMOVE_BUTTON_CLASS_NAME = 'remove-button';

TagFieldHandler.prototype.init = function (currentTags) {
    'use strict';
    
    this.tagInput.addEventListener('keydown', this, false);
    
    if (currentTags) {
        for (const tagName of currentTags) {
            this.addTag(tagName);
        }
    }
};

TagFieldHandler.prototype.handleEvent = function (event) {
    'use strict';
    
    const target = event.target;
    const tagInput = this.tagInput;
    
    if (event.target === tagInput) {
        if (event.key === 'Enter' || event.keyCode === 0x0D || event.key === 'Tab' || event.keyCode === 0x09) {
            event.preventDefault();
            const value = tagInput.value;
            if (value) {
                this.addTag(tagInput.value);
            }
        }
    }
    
    else if (target.classList.contains(TagFieldHandler.REMOVE_BUTTON_CLASS_NAME)) {
        this.removeTag(target.getAttribute('data-tag-name'));
    }
};

TagFieldHandler.prototype.addTag = function (tagName) {
    'use strict';
    
    const tagInput = this.tagInput;
    
    const currentTag = this.getTagElement(tagName);
    if (currentTag) {
        tagInput.value = '';
        highlightUtil.highlight(currentTag);
        return;
    }

    
    const tag = document.createElement('span');
    tag.className = TagFieldHandler.TAG_CLASS_NAME;
    tag.setAttribute('data-tag-name', tagName);
    
    const tagText = document.createElement('span');
    tagText.className = 'text';
    tagText.textContent = tagName;
    tag.appendChild(tagText);
    
    const removeButton = document.createElement('span');
    removeButton.className = TagFieldHandler.REMOVE_BUTTON_CLASS_NAME;
    removeButton.textContent = '\u2715';
    removeButton.setAttribute('data-tag-name', tagName);
    removeButton.addEventListener('click', this, false);
    tag.appendChild(removeButton);
    
    const tagValue = document.createElement('input');
    tagValue.name = this.fieldName;
    tagValue.value = tagName;
    tagValue.type = 'hidden';
    tag.appendChild(tagValue);
    
    
    this.tagContainer.insertBefore(tag, tagInput);
    tagInput.value = '';
};


TagFieldHandler.prototype.removeTag = function (tagName) {
    'use strict';
    
    const targetTag = this.getTagElement(tagName);
    if (targetTag) {
        const tagContainer = this.tagContainer;
        tagContainer.querySelector(`.${TagFieldHandler.REMOVE_BUTTON_CLASS_NAME}[data-tag-name="${tagName}"]`).removeEventListener('click', this, false);
        tagContainer.removeChild(targetTag);
    }
};


TagFieldHandler.prototype.getTagElement = function (tagName) {
    'use strict';
    
    return this.tagContainer.querySelector(`.${TagFieldHandler.TAG_CLASS_NAME}[data-tag-name="${tagName}"]`);
};
