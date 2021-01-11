
function JSONListMatcher(urlPattern, paramName) {
    'use strict';
    
    this.urlPattern = urlPattern;
    this.paramName = paramName;
}

JSONListMatcher.paramReplace = function (pattern, params) {
    'use strict';
    
    const re = /\{([^}]+)\}/g;
    let result = '';
    
    let match;
    let index = 0;
    while (match = re.exec(pattern)) {
        const paramValue = params[match[1]] || '';
        
        result += pattern.substring(index, re.lastIndex - match[0].length);
        result += encodeURIComponent(paramValue);
        index = re.lastIndex;
		
    }
    result += pattern.substring(index);
    
    return result;
};

JSONListMatcher.prototype.fetchMatches = function (current, onMatches) {
    'use strict';
    
    const params = {};
    params[this.paramName] = current;
    
    const headers = new Headers();
    headers.set('Accept', 'application/json');
    
    fetch(JSONListMatcher.paramReplace(this.urlPattern, params), {
        method: 'GET'
        , headers: headers
    }).then((r) => {
        return r.text();
    }).then((t) => {
        const result = JSON.parse(t);
        if (!(result instanceof Array)) {
            throw new Error(`Expected JSON array: ${t}`)
        }
        return result;
    }).then((matches) => {
        onMatches(matches);
    });
};
