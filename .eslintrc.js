module.exports = {
    env: {
        browser: true,
        commonjs: true,
        es6: true,
        node: true
    },
    extends: [
        'eslint:recommended'
    ],
    globals: {
        Atomics: 'readonly',
        SharedArrayBuffer: 'readonly'
    },
    parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module'
    },
    rules: {
        // Error prevention
        'no-console': 'off', // Allow console in Electron apps
        'no-unused-vars': ['error', { 'argsIgnorePattern': '^_' }],
        'no-undef': 'error',
        
        // Code style
        'indent': ['error', 2],
        'linebreak-style': ['error', 'unix'],
        'quotes': ['error', 'single'],
        'semi': ['error', 'always'],
        
        // Best practices
        'eqeqeq': 'error',
        'no-trailing-spaces': 'error',
        'no-multiple-empty-lines': ['error', { 'max': 2 }],
        'comma-dangle': ['error', 'never']
    },
    overrides: [
        {
            files: ['electron_*.js'],
            globals: {
                __dirname: 'readonly',
                process: 'readonly',
                require: 'readonly',
                module: 'readonly',
                exports: 'readonly'
            }
        },
        {
            files: ['renderer*.js', 'preload*.js'],
            env: {
                browser: true
            },
            globals: {
                electronAPI: 'readonly',
                ipcRenderer: 'readonly'
            }
        }
    ]
}; 