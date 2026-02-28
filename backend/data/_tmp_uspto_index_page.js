define([
'jquery.plugins',
'templates/handlebars-compiled',
'framework/keys',
'framework/layoutManager',
'framework/gadgetManager',
'framework/messageManager',
'framework/storageManager',
'framework/windowManager',
'framework/metricsManager',
'widgets/overlay/overlay',
'common/settings',
'common/constants',
'common/_utilities',
'common/focusController',
'pages/index/indexHelper',
'features/workSpaces/workSpaces',
'features/userPreferences/userPreferences',
'features/navigation/searchResultsManager',
'features/searchHistoryManager/searchHistoryManager',
'features/notesManager/notesManager',
'features/shortcuts/shortcuts',
'features/tooManyRequestsOverlay/tooManyRequestsOverlay',
'json!metadata.json',
'widgets/contextualMenu/contextualMenu',
'./indexContextMenuConfig',
'./indexWorkspaceHelper'],
function ($,
HBS,
KEYS,
layoutManager,
gadgetManager,
messageManager,
storageManager,
windowManager,
metricsManager,
Overlay,
settings,
constants,
_utilities,
focusController,
indexHelper,
workSpaces,
userPreferences,
searchResultsManager,
searchHistoryManager,
notesManager,
shortcuts,
tooManyRequestsOverlay,
metadata,
ContextualMenu,
contextMenuConfig,
indexWorkspaceHelper) {

  'use strict';

  var index = {};

  index.data = [];

  index.cases = [];

  index._lastTabIndex = null;

  index.init = function () {
    metricsManager.init();
    storageManager.cleanDb();

    //record index viewer was opened;
    indexHelper.addIndex();

    index.renderLayout();

    notesManager.init();
    focusController.init();

    //Fetch notes for the last accessed workspace
    notesManager.fetchNotesData();

    if (layoutManager.pageMode === 'viewer') {
      index._createContextualMenu();
      workSpaces.renderLayout();
      index.bindListeners();
      tooManyRequestsOverlay.init();
      index.loadData();
    }

    index.bindCommonListeners();
    searchResultsManager.init();
    shortcuts.init();

    if (layoutManager.pageMode === 'viewer') {
      searchHistoryManager.init();
    }

    if (layoutManager.pageMode !== 'viewer') {//only for extended windows
      //Let gadgetManager start loading gadgets
      gadgetManager.openChildWindowGadgets();
    }
    // Access direct document from the current PPUBS window/tab
    if (layoutManager.restoredLayouts) {
      window.setTimeout(function () {
        if (windowManager.getWindow().extSearchParams) {
          let extSearchParams = windowManager.getWindow().extSearchParams;
          messageManager.send({
            action: 'MESSAGE-external-search-trigger',
            options: {
              q: extSearchParams.q,
              db: extSearchParams.db,
              type: extSearchParams.type
            }
          });
        }
      }, 1500);
    }
  };
  index.renderLayout = function () {
    var strHtml = HBS['pages/index/index']({
      viewerMode: layoutManager.pageMode === 'viewer',
      demo: window.CONFIG.demo
    });
    $('body').prepend(strHtml);

    index.$layout = $('body > .layout.ui-layout-container');
    index.$header = $('body > .header.index');
    index.$preferencesOverlay = $('.preferencesOverlay');

    //for now hide the Save As button
    $('.saveAsContainer').hide();

    $(window).trigger('resize');
  };

  index._createContextualMenu = function () {
    this.contextMenuColumn = new ContextualMenu(contextMenuConfig.get('columnMenu'), this.$header.find('.mainbar .right'));
    this.externalLinksContextMenuColumn = new ContextualMenu(contextMenuConfig.get('externalLinksColumnMenu'), this.$header.find('.version'));
  };

  index.renderGadgets = function () {
    //clean up all gadgets belonging to all viewers, incase any are left in storage for any reason.
    // This should fix the blank tab that pops-up on application load.
    gadgetManager.removeAllGadgets();

    var defaultGadgets = [];

    defaultGadgets.push(
      {
        zone: 'center',
        script: 'search',
        active: true,
        window: window.name
      },
      {
        zone: 'west',
        script: 'searchHistory',
        active: true,
        window: window.name
      },

      {
        zone: 'center-south',
        script: 'searchResults',
        active: true,
        window: window.name
      },
      {
        zone: 'center-south',
        script: 'help',
        active: false,
        window: window.name
      },
      {
        zone: 'east',
        script: 'taggedDocument',
        active: false,
        window: window.name
      }
    );

    gadgetManager.setDefaultGadgets(defaultGadgets);
    gadgetManager.renderGadgets();
    $(".header .toolbar").addClass(userPreferences.settings["toolbarIcons"]);
    $(window).trigger('resize');
  };

  index.loadData = function () {
    index.versions = windowManager.getWindow().versions;
    index.renderMeta();
    index.renderUser();
    workSpaces.getCase();
    index.renderGadgets();
    index.handleNumberOfGadgets();

  };

  index.bindCommonListeners = function () {
    $(window).off('keydown.taborder').on('keydown.taborder', this._handleTabOrder.bind(this));

    $(window).on(settings.NAMESPACE + '-message', function (event) {
      var response = event.message,
        action = response.action;

      switch (action) {
        //Access direct document from another window/tab
        case 'MESSAGE-external-search-init':
          if (document['webkitHidden']) {
            var title = document.title;
            if (title.indexOf('(1)') > -1) {
              document.title = title;
            } else {
              document.title = '(1) ' + document.title;
            }
          }

          windowManager.getWindow().extSearchParams = response.options.searchParams;

          //currently no external search requests available.
          if (windowManager.getWindow().extSearchParams) {
            let extSearchParams = windowManager.getWindow().extSearchParams;
            messageManager.send({
              action: 'MESSAGE-external-search-trigger',
              options: {
                q: extSearchParams.q,
                db: extSearchParams.db,
                type: extSearchParams.type
              }
            });
          }
          break;
        case 'MESSAGE-notesViewer-activate':
          var $tab = gadgetManager.getTab('notesViewer', {});
          if ($tab) {
            $tab.click();
          }
          break;
        case 'MESSAGE-gadget-activated':
          index._setTabIndex(response.options.cloneable ? '.tab.' + response.options.script + '[data-gadgetid=' + response.options.data.gadgetId + ']' : '.tab.' + response.options.script);
          break;
        case 'MESSAGE-gadget-loaded':
          if (response.options.window === window.name) {
            window.setTimeout(function () {
              messageManager.send({
                action: 'MESSAGE-session-data',
                script: response.options.script
              });
            }, 1000);
          }
          break;
        case 'MESSAGE-gadget-closed':
          if (response.options.script === "documentViewer") {
            var dvInstancesLeft = gadgetManager.getGadgetsByScript("documentViewer");
            if (dvInstancesLeft.length === 0 && (windowManager.getWindow().SESSION.searchResults === null || $.isEmptyObject(windowManager.getWindow().SESSION.searchResults))) {
              windowManager.getWindow().SESSION.currentDocumentBeingViewed = {};
            }
          }
          break;
        default:
          break;
      }
    });

  };
  index.bindListeners = function () {
    /**
     * handle clicks for all buttons/anchor tags in header
     * Keyup/keydown events are not needed to replicate click functionality for native keyboard events (i.e. - spacebar trigger for button elements)
     *
     * Ignores all buttons in the header which have the class 'idx-click-ignore'. This is because other JS functions currently
     * control their functionality
     */
    this.$header.find('button').not('.idx-click-ignore').off('click').on('click', function (e) {
      let btn = e.currentTarget.classList;
      switch (true) {
        // skip navigation button in header
        case btn.contains('main-skip-nav'):
          $('#skip-nav-target').focus();
          break;
        // gadget/widget buttons in header navigation
        case btn.contains('gadget-menu-btn'):
          let strType = $(this).data('type'),
            strLink = $(this).data('link'),
            strScope = $(this).data('scope'),
            strScript = $(this).data('gadget'),
            data = {};
          if (!e.shiftKey) {
            switch (strType) {
              case 'link':
                if (strScope === 'new') {
                  window.open(strLink);
                }
                if (strScope === 'self') {
                  top.location = strLink;
                }
                break;
              case 'gadget':
                gadgetManager.showGadgetMenu($(this), strScript, data);
                break;
              default:
                break;
            }
          }
          return false;
        default:
          break;
      }
    });

    $(document).off('contextualMenu-item-clicked.' + this.contextMenuColumn.eventNamespace).on('contextualMenu-item-clicked.' + this.contextMenuColumn.eventNamespace, this._handleContextMenuClickEvent.bind(this));

    this.$header.find('.barbutton.new-workspace').off('click').on('click', indexWorkspaceHelper.openOverlay.bind(this));
    this.$header.find('.barbutton.reset-layout').off('click').on('click', indexWorkspaceHelper.openOverlay.bind(this));
  };

  index._handleContextMenuClickEvent = function (evt) {
    const itemData = evt.message.itemData.action;
    switch (itemData) {
      case 'index-help':
        index._openHelper($('#userby'));
        break;
      case 'index-openGlobalDossier':
        _utilities.openLinkInNewTabAsNewProcess(constants.GLOBAL_DOSSIER);
        break;
      case 'index-contactUs':
        let hostName = window.location.hostname;
        let redirectURL = '';
        if (hostName.indexOf('localhost') >= 0) {
          redirectURL = '/static/pages/contact-us.html';
        } else {
          redirectURL = '/pubwebapp/static/pages/contact-us.html';
        }
        _utilities.openLinkInNewTabAsNewProcess(redirectURL);
        break;
      default:
        break;
    }
  };

  index._openHelper = function (originalEl) {
    index.$overlay = new Overlay({
      config: {
        standardModal: true, // temporary flag, to be removed when all overlays are updated to use generic template
        modalSize: constants.MODAL_SIZE_S,
        overlayClassName: 'index_help_overlay',
        title: 'About Patent Public Search',
        content: {
          path: 'pages/index/index_help',
          config: {}
        },
        footerButtons: {
          right: [{
            title: '',
            label: 'OK',
            action: 'close',
            primary: true
          }]
        }
      },
      dragHandle: '.modal-header',
      //bring focus back to originalEl
      returnFocusEl: originalEl,
      buttonClick: index.overlayButtonClick.bind(index)
    });

    index.renderMeta();
  };

  index.overlayButtonClick = function (e) {
    var strAction = $(e.currentTarget).attr('data-action');
    switch (strAction) {
      case 'close':
        if (index.$overlay) {
          index.$overlay.close();
        }
        break;
      default:
    }
  };

  index._getActiveGadgets = function () {
    var sortOrder = ['search', 'searchResults', 'documentViewer', 'searchHistory', 'taggedDocument', 'help'],
      activeGadgets = gadgetManager.getGadgetsByViewerStrict().sort(function (a, b) {
        var sort = sortOrder.indexOf(a.script) - sortOrder.indexOf(b.script);
        return sort;
      }).map(function (x) {
        return x.cloneable ? '.tab.' + x.script + '[data-gadgetid=' + x.data.gadgetId + ']' : '.tab.' + x.script;
      });

    return activeGadgets;
  };

  index._setTabIndex = function (strScript) {
    index._lastTabIndex = index._getActiveGadgets().indexOf(strScript);
  };

  index._handleTabOrder = function (e) {
    e.stopPropagation();

    if (e.ctrlKey && e.shiftKey) {
      var currentIndex,
        activeGadgets = index._getActiveGadgets();

      switch (e.keyCode) {
        case KEYS.COMMA:
          currentIndex = index._lastTabIndex !== null ? index._lastTabIndex - 1 : 0;
          if (currentIndex < 0) {
            currentIndex = activeGadgets.length - 1;
          }
          index._lastTabIndex = currentIndex;

          $(activeGadgets[currentIndex] + ' .title').focus().click();

          break;
        case KEYS.PERIOD:
          currentIndex = index._lastTabIndex !== null ? index._lastTabIndex + 1 : 0;
          if (currentIndex > activeGadgets.length - 1) {
            currentIndex = 0;
          }
          index._lastTabIndex = currentIndex;

          $(activeGadgets[currentIndex] + ' .title').focus().click();

          break;
      }
    }
  };


  index.renderUser = function () {
    $('.header .userby').attr('aria-label', 'Resources');
  };

  index.handleNumberOfGadgets = function () {
    var intNumberOfGadgets = gadgetManager.getGadgets().length;
    $('.header .alert').attr('aria-label', +intNumberOfGadgets + ' gadgets opened');
  };

  index.showSkipContent = function () {
    $('.header .skipcontent').show();
  };

  index.renderMeta = function () {
    var versions = index.versions ? index.versions : [];
    var displayGitCommitId = false;
    //Display GIT commit for all ENVs except for PVT and PROD
    if (window.environment.toUpperCase() === 'LOCAL' ||
    window.environment.toUpperCase() === 'AWSTEST' ||
    window.environment.toUpperCase() === 'AWSDEV' ||
    window.environment.toUpperCase() === 'AWSPERF') {
      displayGitCommitId = true;
    }

    if (versions && versions.length > 0) {

      var versionNum = displayGitCommitId ? metadata.revision[0] : metadata.version;
      windowManager.getWindow().uiVersion = versionNum;

      var apiVersionNum = '';

      if (versions[0]) {
        apiVersionNum = displayGitCommitId ? versions[0].commitId : versions[0].releaseNumber;


        $('.page-title .apptitle .frontend .data').html(versionNum);
        $('.modal-body .content .version').html(versionNum);
        $('.modal-body .content .solr').html(versions[1] && versions[1].releaseNumber);

        $('.modal-body .content .api').html(apiVersionNum);
      }

      if (versions[1]) {
        var collName;
        switch (versions[1].collectionName) {
          case "us_patent_grant":
            collName = "us_patent_grant";
            break;
          case "us_patent_training":
            collName = "Test Data";
            break;
          case "us_patent_c1":
            collName = "C1";
            break;
          case "us_patent_c2":
            collName = "C2";
            break;
          default:
            collName = "us_patent_grant";
            break;
        }
        $('.modal-body .content .solrCollection').html(versions[0] && collName);
      }
    }
  };

  return index;
});
//# sourceMappingURL=index.js.map
