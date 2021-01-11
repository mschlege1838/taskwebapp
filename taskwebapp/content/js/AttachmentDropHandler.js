
function AttachmentDropHandler(dropZone, attachmentListElement) {
    'use strict';
    
    this.dropZone = dropZone;
    this.attachmentListElement = attachmentListElement;
    
    this.dataTransfer = new DataTransfer();
}

AttachmentDropHandler.prototype.init = function () {
    'use strict';
    
    const dropZone = this.dropZone;
    
    dropZone.addEventListener('dragenter', this, false);
    dropZone.addEventListener('dragover', this, false);
    dropZone.addEventListener('dragexit', this, false);
    dropZone.addEventListener('drop', this, false);
    
    for (const removeButton of this.attachmentListElement.getElementsByClassName('remove-button')) {
        removeButton.addEventListener('click', this, false);
    }
};

AttachmentDropHandler.prototype.dispose = function () {
    'use strict';
    
    const dropZone = this.dropZone;
    
    dropZone.removeEventListener('dragenter', this, false);
    dropZone.removeEventListener('dragover', this, false);
    dropZone.removeEventListener('dragexit', this, false);
    dropZone.removeEventListener('drop', this, false);
    
    for (const removeButton of this.attachmentListElement.getElementsByClassName('remove-button')) {
        removeButton.removeEventListener('click', this, false);
    }
    
    delete this.dataTransfer;
};

AttachmentDropHandler.prototype.handleEvent = function (event) {
    'use strict';
    
    const dropZone = this.dropZone;
    const currentTarget = event.currentTarget;

    if (currentTarget === dropZone) {
        switch (event.type) {
            case 'dragenter':
                event.preventDefault();
                dropZone.classList.add('drag-over');
                break;
            case 'dragover':
                event.preventDefault();
                break;
            case 'dragexit':
                dropZone.classList.remove('drag-over');
                break;
            case 'drop':
                dropZone.classList.remove('drag-over');
                const files = event.dataTransfer.files;
                if (!files.length) {
                    return;
                }
                
                event.preventDefault();
                for (let i = 0; i < files.length; ++i) {
                    this.addFile(files[i]);
                }                
                break;
        }
    }
    
    else if (currentTarget.classList.contains('remove-button') && event.button === 0) {
        this.removeFile(currentTarget.getAttribute('data-file-name'));
    }
};

AttachmentDropHandler.prototype.addFile = function (file) {
    'use strict';
    
    const dataTransfer = this.dataTransfer;
    const attachmentListElement = this.attachmentListElement;
    
    // If current attachment exists with same name, remove entirely; replace with new.
    this.removeFile(file.name);

    // Create new attachment element.
    const attachmentElement = document.createElement('li');
    attachmentElement.className = 'attachment new';
    attachmentElement.setAttribute('data-file-name', file.name);
    attachmentListElement.appendChild(attachmentElement);
    
    const attachmentText = document.createElement('span');
    attachmentText.className = 'text';
    attachmentText.textContent = file.name;
    attachmentElement.appendChild(attachmentText);
    
    const removeButton = document.createElement('span');
    removeButton.className = 'remove-button';
    removeButton.textContent = '\u2715';
    removeButton.setAttribute('data-file-name', file.name);
    attachmentElement.appendChild(removeButton);
    removeButton.addEventListener('click', this, false);
    
    // Add file to cache.
    dataTransfer.items.add(file);
    
};

AttachmentDropHandler.prototype.removeFile = function (name) {
    'use strict';
    
    const dataTransfer = this.dataTransfer;
    const attachmentListElement = this.attachmentListElement;
    
    const current = attachmentListElement.querySelector(`.attachment[data-file-name="${name.replaceAll('"', '\\"')}"]`);
    if (current) {
        attachmentListElement.removeChild(current);
        current.getElementsByClassName('remove-button')[0].removeEventListener('click', this, false);
        
        for (let i = 0; i < dataTransfer.items.length; ++i) {
            if (dataTransfer.items[i].name == name) {
                dataTransfer.items.remove(i);
                break;
            }
        }
    }
};
