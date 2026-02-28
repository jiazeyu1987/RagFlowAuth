function ownKeys(e, r) {var t = Object.keys(e);if (Object.getOwnPropertySymbols) {var o = Object.getOwnPropertySymbols(e);r && (o = o.filter(function (r) {return Object.getOwnPropertyDescriptor(e, r).enumerable;})), t.push.apply(t, o);}return t;}function _objectSpread(e) {for (var r = 1; r < arguments.length; r++) {var t = null != arguments[r] ? arguments[r] : {};r % 2 ? ownKeys(Object(t), !0).forEach(function (r) {_defineProperty(e, r, t[r]);}) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) {Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r));});}return e;}function _defineProperty(e, r, t) {return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e;}function _toPropertyKey(t) {var i = _toPrimitive(t, "string");return "symbol" == typeof i ? i : i + "";}function _toPrimitive(t, r) {if ("object" != typeof t || !t) return t;var e = t[Symbol.toPrimitive];if (void 0 !== e) {var i = e.call(t, r || "default");if ("object" != typeof i) return i;throw new TypeError("@@toPrimitive must return a primitive value.");}return ("string" === r ? String : Number)(t);}define([
'jquery',
'framework/messageManager',
'framework/services',
'framework/storageManager',
'common/constants',
'store/middleware/APIQueue'],
function ($,
messageManager,
services,
storageManager,
constants,
APIQueue) {
  'use strict';

  const apiQueue = new APIQueue.default({ autoDequeue: false });
  let authInProgress = false;
  var serviceManager;

  const fetch = (url, options = {}) => {
    const timeout = options.timeout || constants.API_TIMEOUT;
    const timeoutErr = {
      ok: false,
      status: 0,
      statusText: 'timeout'
    };
    return new Promise(function (resolve, reject) {
      window.fetch(url, options).then(resolve, reject);
      setTimeout(reject.bind(null, timeoutErr), timeout);
    });
  };

  const authUser = () => {
    let sessionId = storageManager.get(constants.ADVANCED_SESSION_KEY);
    if (!sessionId) {
      sessionId = -1;
    }

    if (authInProgress) {
      return;
    }

    authInProgress = true;

    return fetch(services.getUrl('user.data', {}), {
      method: 'POST',
      timeout: constants.API_USER_TIMEOUT,
      body: sessionId
    }).then((response) => {
      //US496779 Store the access token in local storage instead of session
      localStorage.setItem(constants.ACCESS_TOKEN_KEY, response.headers.get('x-access-token'));
      return response.json();
    }).then((response) => {
      storageManager.set(constants.ADVANCED_SESSION_KEY, response.userSessionId);
      window.userSessionId = response.userSessionId;
      window.caseId = response.userCase.caseId;
    }).finally(() => {
      authInProgress = false;
      apiQueue.dequeue();
    });
  };

  const replaceURLWithUpdatedCase = (url, oldCaseID) => {
    if (url.includes(`/${oldCaseID}`)) {
      return url.replace(`/${oldCaseID}`, `/${window.caseId}`);
    } else if (url.includes(`?caseId=${oldCaseID}`)) {
      return url.replace(`?caseId=${oldCaseID}`, `?caseId=${window.caseId}`);
    }

    return url;
  };

  const replaceDataWithUpdatedCase = (data) => {
    if (typeof data === 'object' || data === "") {
      return data;
    }

    const jsonData = JSON.parse(data);

    if (jsonData && jsonData.hasOwnProperty('caseId')) {
      jsonData['caseId'] = window.caseId;
    }

    if (jsonData && jsonData.hasOwnProperty('query') && jsonData['query'].hasOwnProperty('caseId')) {
      jsonData['query']['caseId'] = window.caseId;
    }

    return JSON.stringify(jsonData);
  };

  $.ajaxPrefilter(function (opts, originalOpts, jqXHR) {
    // deferred object to handle done/fail callbacks
    const dfd = $.Deferred();

    // if the request works, return normally
    jqXHR.done((...args) => {
      if (originalOpts.customSuccess) {
        originalOpts.customSuccess.apply(originalOpts, args);
      }
      dfd.resolve.apply(dfd, args);
    });

    // if the request fails, enqueue the request until it succeeds
    jqXHR.fail(function (error) {
      const args = Array.prototype.slice.call(arguments);
      const oldCaseID = window.caseId;

      if (jqXHR.status === 401) {
        // lets queue the request
        apiQueue.enqueue(
          () =>
          new Promise((resolve, reject) => {
            // call the api again once authentication iframe has loaded
            // (this is done by dequeue method of apiQueue)
            $.ajax(_objectSpread(_objectSpread({},
            originalOpts), {}, {
              headers: _objectSpread(_objectSpread({},
              originalOpts.headers), {}, {
                'x-access-token': localStorage.getItem(constants.ACCESS_TOKEN_KEY) }),

              url: replaceURLWithUpdatedCase(originalOpts.url, oldCaseID),
              data: replaceDataWithUpdatedCase(originalOpts.data) })
            ).done((...args) => {
              resolve.apply(void 0, args);
              dfd.resolve.apply(dfd, args);
            }).fail((...args) => {
              reject.apply(void 0, args);
              dfd.reject.apply(dfd, args);
            });
          })
        );

        // attempt to get the UI to reauthorize
        authUser();
      } else {
        if (originalOpts.customError) {
          originalOpts.customError(error, error.statusText);
        }
        dfd.rejectWith(jqXHR, args);

        if (!originalOpts.customIgnoreRedirect) {
          serviceManager.sendNotification(error.status, originalOpts.customNotification);
        }
      }
    });

    // NOW override the jqXHR's promise functions with our deferred
    return dfd.promise(jqXHR);
  });

  serviceManager = {
    exec: function (options, ignoreRedirect = false) {
      // contentType is the type of data the application is sending to the API
      var defaults = {
          type: 'GET',
          url: '',
          contentType: 'application/json',
          async: true,
          params: {},
          headers: {},
          notification: true //when true, sends out a notification in case of error.
        },
        timeout = constants.API_TIMEOUT,
        ajaxRequest;

      /*extend default with options;*/
      options = $.extend({}, defaults, options);

      if (window.CONFIG.mock && options.type !== 'GET') {
        return;
      }

      const headers = _objectSpread(_objectSpread({},
      options.headers), {}, {
        'x-access-token': localStorage.getItem(constants.ACCESS_TOKEN_KEY) });


      const ajaxOptions = {
        timeout: options.timeout || timeout,
        type: options.type,
        url: options.url,
        data: options.params || null,
        headers: headers,
        contentType: options.contentType,
        async: options.async,
        customIgnoreRedirect: ignoreRedirect,
        customNotification: options.notification,
        customSuccess: options.success || null,
        customError: options.error || null
      };

      // if dataType is specified.. add it to the options
      if (options.dataType !== undefined) {
        ajaxOptions['dataType'] = options.dataType;
      }

      ajaxRequest = $.ajax(ajaxOptions);

      return ajaxRequest;
    },

    sendNotification: function (status, notification) {
      if (status === 500 && notification) {
        messageManager.send({
          action: "MESSAGE-workSpace-notification",
          data: {
            message: 'Unable to process the request. Please try again later.',
            type: "error",
            timeout: constants.NOTIFICATIONS_TIMEOUT,
            visible: true
          }
        });

        //hide the loading gear.
        serviceManager.hideLoader();
      }
    },

    hideLoader: function () {
      $(".loadingSpinnerOverlay").hide();
      $(".loadingButton").hide();
    },
    /*
     * fetches a request like the normal fetch function 
     * but with a timeout argument added.
     */
    fetch: function (...args) {
      return fetch.apply(void 0, args);
    },
    exec_importMultipleFiles: function exec_importMultipleFiles(options) {
      var defaults = {
          url: '',
          type: 'POST',
          data: '',
          cache: false,
          dataType: '',
          processData: false,
          contentType: false,
          notification: true //when true, sends out a notification in case of error.
        },
        timeout = 120000,
        ajaxRequest;

      /*extend default with options;*/
      options = $.extend({}, defaults, options);

      ajaxRequest = $.ajax({
        timeout: options.timeout || timeout,
        type: options.type,
        data: options.data,
        cache: false,
        dataType: options.dataType,
        processData: false,
        contentType: false,
        url: options.url,
        success: options.success || null,
        error: options.error || null,
        async: options.async
      });

      ajaxRequest.fail(function (xhr) {
        serviceManager.sendNotification(xhr.status, options.notification);
      });

      return ajaxRequest;
    }
  };

  return serviceManager;
});
//# sourceMappingURL=serviceManager.js.map
