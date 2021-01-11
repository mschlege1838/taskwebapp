

const highlightUtil = {
    HIGHLIGHTED_CLASS_NAME: 'highlighted'
    
    , highlight: function (el) {
        'use strict';
        
        el.classList.add(highlightUtil.HIGHLIGHTED_CLASS_NAME);
        el.addEventListener('animationend', highlightUtil.clearHighlight, false);
    }
    
    , clearHighlight: function (event) {
        'use strict';
        
        const target = event.target;
        target.classList.remove(highlightUtil.HIGHLIGHTED_CLASS_NAME);
        target.removeEventListener('animationend', highlightUtil.clearHighlight, false);
    }
}