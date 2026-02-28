define([
'jquery',
'framework/uriManager',
'framework/storageManager',
'common/constants',
'common/user',
'common/settings',
'maxZIndex'],
function ($,
uriManager,
storageManager,
constants,
user,
settings)
{

  'use strict';

  return {
    getViewerFromURL: function () {
      const url = window.location.pathname;
      const strViewer = url.substring(url.lastIndexOf('/') + 1).replace('.html', '');

      return strViewer || 'index';
    },

    displayAlreadyOpenedError: function (strViewer) {
      // Check if  there are any opened consoles, if not giving it a value just to pass the check, otherwise get the expired seconds to check if the browser has crashed
      const currentTimeStamp = new Date().getTime();
      const expiredSeconds = storageManager.get(settings.NAMESPACE + '-opened') === null ? 3500 : currentTimeStamp - JSON.parse(storageManager.get(settings.NAMESPACE + '-opened')).expiredSeconds;
      const isOpen = expiredSeconds < 3000;

      //Check if expired seconds is less than 3 seconds; expired seconds should always about 2 seconds but check for 3 seconds just to count for any delays
      if (isOpen && strViewer === 'index' && uriManager.get('extended') !== '1') {
        $('body').html('<p style="padding:0 0 0 20px;">Patent Public Search Console is already open.</p>');
        setTimeout(window.close, 10000);
        return true;
      }

      return false;
    },

    init: function () {
      const context = this;

      const strViewer = context.getViewerFromURL();

      if (context.displayAlreadyOpenedError(strViewer)) {
        // don't do anything if application is already opened
        return;
      }

      //clean up localStorage in case of any loose references.
      if (strViewer === 'index' && uriManager.get('extended') !== '1') {
        storageManager.removeAll();
      }

      var strViewerScript = ['pages', strViewer, strViewer].join('/');

      user.fetchUser(strViewer).done(function () {
        context._openViewer(strViewerScript, strViewer);
      }).fail(function (errorCode) {
        if (errorCode === 403) {
          context._openErrorPage(constants.PAGE_NO_ACCESS);
        } else {
          console.log(errorCode + ' Unable to get API initially');
        }
      });

    },


    _openViewer: function (strViewerScript, strViewer) {
      require([
      'framework/windowManager',
      'framework/layouts',
      'framework/layoutManager',
      'framework/gadgetManager',
      'features/sessionManager/sessionManager',
      'features/tagManager/tagManager',
      'store/store-plain',
      'store/interface/preferenceInterface',
      strViewerScript],

      function (windowManager,
      layouts,
      layoutManager,
      gadgetManager,
      sessionManager,
      tagManager,
      store,
      preferenceInterface,
      page) {
        //US386058 handle external query search, (strViewer === 'classification')can be added for classification search if needed 
        if (strViewer === 'external') {
          page.init();
        } else {
          store.init();
          if (strViewer === 'index' && uriManager.get('extended') !== '1') {
            storageManager.cleanDb();
          }
          preferenceInterface.init();
          sessionManager.init();
          windowManager.init();
          tagManager.init();
          layouts.getLayoutState().done(function () {
            layoutManager.init();
            gadgetManager.init();
            page.init();
          });
        }
      }
      );
    },

    _openErrorPage: function (url) {
      window.location.replace(url);
    }
  };
});
//# sourceMappingURL=bootstrap.js.map
