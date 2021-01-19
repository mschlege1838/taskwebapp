
function NotesHandler(addButton, notesListElement, form, pinnedListElement) {
    'use strict';
    
    this.addButton = addButton;
    this.notesListElement = notesListElement;
    this.form = form;
    this.pinnedListElement = pinnedListElement;
    
    this.localIdCounter = 0
    this.attachmentHandlers = new Map();
    this.dragHandlers = new Map()
}

NotesHandler.DRAG_DROP_EXCLUDED_TAGS = ['TEXTAREA', 'A'];
NotesHandler.DRAG_DROP_EXCLUDED_CLASSES = ['remove-button', 'unpin-button', 'drop-zone'];

NotesHandler.prototype.deltaX = null;
NotesHandler.prototype.deltaY = null;
NotesHandler.prototype.targetContainer = null;

NotesHandler.prototype.init = function () {
    'use strict';
    
    this.addButton.addEventListener('click', this, false);
    this.form.addEventListener('submit', this, false);
    
    const attachmentHandlers = this.attachmentHandlers;
    for (const container of document.getElementsByClassName('note-container')) {
        const pinned = container.classList.contains('pinned');
        if (pinned) {
            container.addEventListener('mousedown', this, false);
        }
        
        container.getElementsByClassName(pinned ? 'unpin-button' : 'pin-button')[0].addEventListener('click', this, false);
        container.getElementsByClassName('remove-button')[0].addEventListener('click', this, false);
        
        const dropHandler = new AttachmentDropHandler(container.getElementsByClassName('drop-zone')[0], container.getElementsByClassName('attachment-list')[0])
        dropHandler.init();
        attachmentHandlers.set(container.getElementsByClassName('note')[0].id, dropHandler);
    }
};

NotesHandler.prototype.handleEvent = function (event) {
    'use strict';
    
    const currentTarget = event.currentTarget;
    
    if (currentTarget === this.addButton) {
        this.addNote();
    }
    
    else if (currentTarget === this.form) {
       this.doSubmit();
    }
    
    else if (currentTarget.classList && currentTarget.classList.contains('remove-button') && event.button === 0) {
        this.removeNote(currentTarget.getAttribute('data-container-id'));
    }
    
    else if (currentTarget.classList && currentTarget.classList.contains('pin-button') && event.button === 0) {
        this.pinNote(currentTarget.getAttribute('data-container-id'));
    }
    
    else if (currentTarget.classList && currentTarget.classList.contains('unpin-button') && event.button === 0) {
        this.unpinNote(currentTarget.getAttribute('data-container-id'));
    }
    
    else if (event instanceof MouseEvent) {
        this.handlePinnedDrag(event);
    }

};

NotesHandler.prototype.handlePinnedDrag = function (event) {
    'use strict';
    
    switch (event.type) {
        case 'mousemove': {
            
            if (event.buttons !== 1) {
                this.dropPinned();
            } else {
                const targetContainer = this.targetContainer;
                const offsetParent = targetContainer.offsetParent;
                
                let newTop = offsetParent.scrollTop + event.clientY - this.deltaY;
                let newLeft = offsetParent.scrollLeft + event.clientX - this.deltaX;
                
                if (newTop < 0) {
                    newTop = 0;
                } else if (newTop + targetContainer.offsetHeight > offsetParent.offsetHeight) {
                    newTop = offsetParent.offsetHeight - targetContainer.offsetHeight;
                }
                
                if (newLeft < 0) {
                    newLeft = 0;
                }else if (newLeft + targetContainer.offsetWidth > offsetParent.offsetWidth) {
                    newLeft = offsetParent.offsetWidth - targetContainer.offsetWidth;
                }
                
                targetContainer.style.top = newTop + 'px';
                targetContainer.style.left = newLeft + 'px';
                
                this.checkPinnedPosition(targetContainer);
            }
            break;
        }
        case 'mousedown': {
            const target = event.target;
            if (NotesHandler.DRAG_DROP_EXCLUDED_TAGS.indexOf(target.tagName) !== -1) {
                return;
            }
            for (const excludedClass of NotesHandler.DRAG_DROP_EXCLUDED_CLASSES) {
                if (target.classList.contains(excludedClass)) {
                    return;
                }
            }
            
            const currentTarget = event.currentTarget;
            const offsetParent = currentTarget.offsetParent;
            
            this.deltaY = offsetParent.scrollTop + event.clientY - currentTarget.offsetTop;
            this.deltaX = offsetParent.scrollLeft + event.clientX - currentTarget.offsetLeft;
            
            offsetParent.addEventListener('mousemove', this, false);
            offsetParent.style['min-height'] = currentTarget.offsetHeight + 'px';
            window.addEventListener('mouseup', this, false);
            
            currentTarget.style.position = 'absolute';
            
            this.targetContainer = currentTarget;
            break;
        }
        case 'mouseup':
            this.dropPinned();
            break;
    }
};

NotesHandler.prototype.checkPinnedPosition = function (currentTarget) {
    'use strict';
    
    const aLeft = currentTarget.offsetLeft;
    const aRight = aLeft + currentTarget.offsetWidth;
    const aTop = currentTarget.offsetTop;
    const aBottom = aTop + currentTarget.offsetHeight;
    
    for (const container of this.pinnedListElement.getElementsByClassName('note-container')) {
        if (container === currentTarget) {
            continue;
        }
        
        const bLeft = container.offsetLeft;
        const bRight = bLeft + container.offsetWidth;
        const bTop = container.offsetTop;
        const bBottom = bTop + container.offsetHeight;
        
        if ((aLeft >= bLeft && aLeft <= bRight && aTop >= bTop && aTop <= bBottom) || (aRight <= bRight && aRight >= bLeft && aBottom <= bBottom && aBottom >= bTop)) {
            container.classList.add('pinned-over');
        } else {
            container.classList.remove('pinned-over');
        }
    }
    
};

NotesHandler.prototype.dropPinned = function () {
    'use strict';
    
    const currentTarget = this.targetContainer;
    
    currentTarget.offsetParent.removeEventListener('mousemove', this, false);
    window.removeEventListener('mouseup', this, false);
    currentTarget.style.position = 'static';
    currentTarget.style.top = currentTarget.style.left = currentTarget.offsetParent.style['min-height'] = 'initial';
    
    const pinnedListElement = this.pinnedListElement;
    pinnedListElement.removeChild(currentTarget);
    
    const over = pinnedListElement.getElementsByClassName('pinned-over')[0];
    if (over) {
        pinnedListElement.insertBefore(currentTarget, over);
        over.classList.remove('pinned-over');
    } else {
        pinnedListElement.appendChild(currentTarget);
    }
    
    this.targetContainer = null;
};

NotesHandler.prototype.doSubmit = function () {
    'use strict';
    
    const form = this.form;
    
    for (const item of this.attachmentHandlers) {
        const name = item[0];
        const handler = item[1];
        
        if (!handler.dataTransfer.files.length) {
            continue;
        }
        
        const attachmentsInput = document.createElement('input');
        attachmentsInput.className = 'attachments-input';
        attachmentsInput.type = 'file';
        attachmentsInput.name = `${name}_newAttachments`;
        attachmentsInput.multiple = true;
        attachmentsInput.files = handler.dataTransfer.files;
        
        form.appendChild(attachmentsInput);
    }
    
    const pinnedNotes = this.pinnedListElement.getElementsByClassName('note-container');
    for (let i = 0; i < pinnedNotes.length; ++i) {
        const container = pinnedNotes[i];
        
        const pinnedOrderInput = document.createElement('input');
        pinnedOrderInput.type = 'hidden';
        pinnedOrderInput.name = `${container.getElementsByClassName('note')[0].id}_pinned`;
        pinnedOrderInput.value = i;
        
        form.appendChild(pinnedOrderInput);
    }
    
};

NotesHandler.prototype.addNote = function () {
    'use strict';
    
    const notesListElement = this.notesListElement;
    
    // Generate IDs.
    const id = this.localIdCounter + 1
    
    const noteId = `newNote_${id}`;
    const attachmentDropZoneId = `${noteId}_attachmentDropZone`;
    const containerId = `${noteId}_container`;
    
    // Insert new item.
    notesListElement.insertAdjacentHTML('afterbegin', `
    <li class="note-container" id="${containerId}">
        <div class="note-header">
            <label for="${attachmentDropZoneId}">Attachments</label><!--
            --><span class="controls">
                <span class="pin-button" data-container-id="${containerId}"></span>
                <span class="remove-button" data-container-id="${containerId}">&#x2715;</span>
            </span>
        </div>
        <ul class="attachment-list"></ul>
        <div id="${attachmentDropZoneId}" class="drop-zone">Drop Attachments Here</div>
        <textarea id="${noteId}" name="${noteId}" class="note"></textarea>
    </li>
    `);
    const container = document.getElementById(containerId);

    // Register event listeners.
    container.getElementsByClassName('remove-button')[0].addEventListener('click', this, false);
    container.getElementsByClassName('pin-button')[0].addEventListener('click', this, false);
    
    const dropHandler = new AttachmentDropHandler(document.getElementById(attachmentDropZoneId), container.getElementsByClassName('attachment-list')[0]);
    dropHandler.init();
    this.attachmentHandlers.set(noteId, dropHandler);
    
    // Increment local ID counter.
    this.localIdCounter = id;
};


NotesHandler.prototype.removeNote = function (containerId) {
    'use strict';
    
    const container = document.getElementById(containerId);
    
    const noteId = container.getElementsByClassName('note')[0].id;
    const attachmentHandlers = this.attachmentHandlers;
    attachmentHandlers.get(noteId).dispose();
    attachmentHandlers.delete(noteId);
    
    container.getElementsByClassName('remove-button')[0].removeEventListener('click', this, false);
    
    if (container.classList.contains('pinned')) {
        container.removeEventListener('mousedown', this, false);
        container.getElementsByClassName('unpin-button')[0].removeEventListener('click', this, false);
        this.pinnedListElement.removeChild(container);
    } else {
        container.getElementsByClassName('pin-button')[0].removeEventListener('click', this, false);
        this.notesListElement.removeChild(container);
    }
};


NotesHandler.prototype.pinNote = function (containerId) {
    'use strict';
    
    const pinnedListElement = this.pinnedListElement;
    
    const container = document.getElementById(containerId);
    container.classList.add('pinned');
    
    const pinButton = container.getElementsByClassName('pin-button')[0];
    pinButton.classList.remove('pin-button');
    pinButton.classList.add('unpin-button');
    
    container.addEventListener('mousedown', this, false);
    
    this.pinnedListElement.appendChild(container);
};


NotesHandler.prototype.unpinNote = function (containerId) {
    'use strict';
    
    const container = document.getElementById(containerId);
    container.classList.remove('pinned');
    
    const pinButton = container.getElementsByClassName('unpin-button')[0];
    pinButton.classList.remove('unpin-button');
    pinButton.classList.add('pin-button');
    
    container.removeEventListener('mousedown', this, false);
    
    this.notesListElement.appendChild(container);
};
