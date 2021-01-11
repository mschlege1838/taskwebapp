function OffsetCoordinates(x, y) {
    'use strict';
    
    this.x = x;
    this.y = y;
};

OffsetCoordinates.getOffset = function (element) {
    'use strict';
    
    var coordinates = new OffsetCoordinates(element.offsetLeft, element.offsetTop);
    OffsetCoordinates._getOffset(element.offsetParent, coordinates);
    return coordinates;
};

OffsetCoordinates._getOffset = function (element, coordinates) {
    'use strict';
    
    if (!element) {
        return;
    }
    
    coordinates.x += element.offsetLeft;
    coordinates.y += element.offsetTop;
    OffsetCoordinates._getOffset(element.offsetParent, coordinates);
};