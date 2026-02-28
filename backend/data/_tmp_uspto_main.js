/* global require: true */
require.config({
  baseUrl: '',
  urlArgs: 'bust=' + new Date().getTime(),
  map: {
    '*': {
      'css': 'vendor/require/css.min',
      'text': 'vendor/require/text',
      'json': 'vendor/require/json'
    }
  },
  paths: {
    'jquery.plugins': 'vendor/jquery.plugins/jquery.plugins',

    // AMD exposed modules
    'jquery': 'vendor/jquery/jquery.min',
    'jqueryui': 'vendor/jquery-ui/jquery-ui.min',
    'handlebars': 'vendor/handlebars/handlebars.runtime.min',

    // Compiled handlebars templates
    'handlebars-helpers': 'common/handlebars-helpers',
    'handlebars-utilities': 'common/handlebars-utilities',
    'handlebars-compiled': 'templates/handlebars-compiled',

    'html2canvas': 'vendor/html2canvas/html2canvas.min',

    // Plugins that need to be shimmed
    'tooltip': 'vendor/bootstrap/tooltip',
    'popover': 'vendor/bootstrap/popover',
    'barCode': 'vendor/jquery.barcode/jquery-barcode.min',
    'modernizr': 'vendor/modernizr/modernizr',
    'pgwbrowser': 'vendor/pgwbrowser/pgwbrowser',
    'slickgrid/slick.grid': 'vendor/slickgrid/slick.grid',
    'slickgrid/slick.dataview': 'vendor/slickgrid/slick.dataview',
    'slickgrid/slick.core': 'vendor/slickgrid/slick.core',
    'slickgrid/slick.remotemodel': 'vendor/slickgrid/slick.remotemodel',
    'slickgrid/dragEvent': 'vendor/slickgrid/lib/jquery.event.drag-2.2',
    'slickgrid/dropEvent': 'vendor/slickgrid/lib/jquery.event.drop-2.2',
    'slickgrid/slick.formatters': 'vendor/slickgrid/slick.formatters',
    'slickgrid/slick.groupitemmetadataprovider': 'vendor/slickgrid/slick.groupitemmetadataprovider',
    'slickgrid/slick.cellrangedecorator': 'vendor/slickgrid/plugins/slick.cellrangedecorator',
    'slickgrid/slick.cellrangeselector': 'vendor/slickgrid/plugins/slick.cellrangeselector',
    'slickgrid/slick.cellselectionmodel': 'vendor/slickgrid/plugins/slick.cellselectionmodel',
    'slickgrid/slick.rowselectionmodel': 'vendor/slickgrid/plugins/slick.rowselectionmodel',

    'linq': 'vendor/jquery.linq/jquery.linq.min',
    'uilayout': 'vendor/jquery-layout/jquery-layout',
    'maxZIndex': 'vendor/jquery.maxZIndex/jquery.maxZIndex',
    'hasAttr': 'vendor/jquery.hasAttr/jquery.hasAttr',
    'throttle-debounce': 'vendor/jquery.throttle-debounce/jquery.ba-throttle-debounce',
    'highlight': 'vendor/jquery.highlight/jquery.highlight',
    'aop': 'vendor/jquery.aop/jquery-aop',
    'trix': 'vendor/trix-build/dist/trix-core',
    'jqTree': 'vendor/tree.jquery/tree.jquery',
    'contextMenu': 'vendor/jquery.contextMenu/jquery.contextMenu',
    'multiselect': 'vendor/jquery.multiselect/jquery.multiselect',
    'customMultiselect': 'vendor/multiselect/multiselect',
    'customDatepicker': 'common/custom/customDatepicker',
    'dexie': 'vendor/dexie/dexie.min',
    'Mousetrap': 'vendor/mousetrap/mousetrap.min',
    'redux': 'vendor/redux/dist/redux.min',
    'redux-thunk': 'vendor/redux-thunk-2.3.0/src/index',
    'redux-state-sync': 'vendor/redux-state-sync/dist/syncState.umd',
    'lodash': 'vendor/lodash/lodash',
    'deep-object-diff': 'vendor/deep-object-diff-1.1.0/dist/diff/index',
    'deep-object-diff-deleted': 'vendor/deep-object-diff-1.1.0/dist/deleted/index',
    'deep-object-utils': 'vendor/deep-object-diff-1.1.0/dist/utils/index'
  },
  shim: {

    'barCode': { deps: ['jquery'] },
    'deep-object-diff': {
      deps: ['deep-object-utils']
    },
    'modernizr': {
      exports: 'Modernizr'
    },
    'pgwbrowser': {
      exports: '$.pgwBrowser',
      deps: ['jquery']
    },
    'slickgrid/dragEvent': {
      exports: '$.fn.drag',
      deps: ['jquery']
    },
    'slickgrid/dropEvent': {
      exports: '$.fn.drop',
      deps: ['jquery']
    },
    'slickgrid/slick.core': {
      exports: 'Slick',
      deps: ['jquery']
    },
    'slickgrid/slick.grid': {
      deps: ['jquery', 'slickgrid/slick.core', 'slickgrid/dragEvent', 'slickgrid/dropEvent']
    },
    'slickgrid/slick.remotemodel': {
      deps: ['slickgrid/slick.grid']
    },
    'slickgrid/slick.dataview': {
      deps: ['slickgrid/slick.grid']
    },
    'slickgrid/slick.formatters': {
      exports: 'Slick.Formatters',
      deps: ['jquery']
    },
    'slickgrid/slick.groupitemmetadataprovider': {
      deps: ['jquery']
    },
    'slickgrid/slick.cellrangedecorator': {
      deps: ['jquery']
    },
    'slickgrid/slick.cellrangeselector': {
      deps: ['jquery']
    },
    'slickgrid/slick.cellselectionmodel': {
      deps: ['jquery']
    },
    'slickgrid/slick.rowselectionmodel': {
      deps: ['jquery']
    },
    'uilayout': {
      exports: '$.layout',
      deps: ['jquery', 'jqueryui']
    },
    'linq': {
      deps: ['jquery']
    },
    'maxZIndex': {
      exports: '$.maxZIndex',
      deps: ['jquery']
    },
    'hasAttr': {
      exports: '$.fn.hasAttr',
      deps: ['jquery']
    },
    'throttle-debounce': {
      deps: ['jquery']
    },
    'trix': {
      deps: ['jquery']
    },
    'highlight': {
      deps: ['jquery']
    },
    'aop': {
      exports: '$.aop',
      deps: ['jquery']
    },
    'jqTree': {
      deps: ['jquery']
    },
    'contextMenu': {
      deps: ['jquery']
    },
    'customMultiselect': {
      exports: '$.fn.customMultiselect',
      deps: ['jquery']
    },
    'multiselect': {
      deps: ['jquery']
    },
    'tooltip': {
      deps: ['jquery', 'jqueryui']
    },
    'customDatepicker': {
      deps: ['jquery', 'jqueryui']
    },
    'popover': {
      deps: ['tooltip']
    }
  },
  waitSeconds: 0,
  wrapShim: true,
  deps: ['common/settings']

});

require(['jquery', 'framework/storageManager', 'shared'], function ($, storageManager) {
  'use strict';

  var defaultConfig = {
      debug: false,
      mock: false,
      demo: false,
      metrics: false,
      metricsCount: 100,
      showInsetInOpener: false,
      preload: true
    },
    config = storageManager.get('est-config');

  if (config) {
    config = JSON.parse(config);
  }

  config = $.extend(defaultConfig, config);
  window.CONFIG = config;
  window.SESSION = {};


  require(['bootstrap'], function (bootstrap) {
    bootstrap.init();
  });

});
//# sourceMappingURL=main.js.map
