
// Imports
const path = require('path');
const fs = require('fs');
const gulp = require('gulp');
const uglifyjs = require('gulp-uglify');
const uglifycss = require('gulp-uglifycss');
const rename = require('gulp-rename');


// Config
const OUT_DIR = 'include';

const OUT_SRC_FILE_NAME = 'autocomplete-input.js';
const SRC_FILES = [
    'src/OffsetCoordinates.js'
    , 'src/AutoCompleteInput.js'
];

const OUT_CSS_FILE_NAME = 'autocomplete-input.css';
const CSS_FILES = [
    'style/autocomplete-input.css'
];





// Util
function mkdir(target) {
    'use strict';
    
    return new Promise((resolve, reject) => {
        fs.mkdir(target, (err) => {
            if (err && err.code !== 'EEXIST') {
                reject(err);
            }
            resolve();
        });
    });
}


function cat(targetDir, targetFile, files) {
    'use strict';
    
    let chain = mkdir(targetDir).then(() => {
        return fs.createWriteStream(path.join(targetDir, targetFile));
    });
    
    
    for (const srcFile of files) {
        chain = chain.then((writer) => {
            return new Promise((resolve, reject) => {
                function onError(err) {
                    reject(err);
                }
                
                const reader = fs.createReadStream(srcFile);
                reader.on('end', () => {
                    writer.removeListener('error', onError);
                    resolve(writer);
                });
                reader.on('error', onError);
                writer.on('error', onError);
                reader.pipe(writer, {end: false});
            });
        });
    }
    
    return chain.then((writer) => {
        writer.end();
    });
}


// Targets
function catSrc() {
    'use strict';
    
    return cat(OUT_DIR, OUT_SRC_FILE_NAME, SRC_FILES);
}

function catCSS() {
    'use strict';
    
    return cat(OUT_DIR, OUT_CSS_FILE_NAME, CSS_FILES);
}


function minifySrc() {
    'use strict';
    
    return gulp.src(`${OUT_DIR}/${OUT_SRC_FILE_NAME}`)
        .pipe(uglifyjs())
        .pipe(rename({ extname: '.min.js'}))
        .pipe(gulp.dest(OUT_DIR));
}

function minifyCSS() {
    'use strict';
    
    return gulp.src(`${OUT_DIR}/${OUT_CSS_FILE_NAME}`)
        .pipe(uglifycss())
        .pipe(rename({ extname: '.min.css'}))
        .pipe(gulp.dest(OUT_DIR));
}

// Exports
exports.default = gulp.series(
    gulp.parallel(catSrc, catCSS)
    , gulp.parallel(minifySrc, minifyCSS)
);