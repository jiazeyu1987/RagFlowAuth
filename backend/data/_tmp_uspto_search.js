/**
 * Created by scamara on 2/15/2016.
 */
/**
 * Search.JS view
 * @description controls search widget view
 * @param {object} $
 * @param {object} fitCountriesOverlay
 * @param {object} fitHelper
 * @param {object} windowManager
 * @param {object} messageManager
 * @param {object} services
 * @param {object} serviceManager
 * @param {object} keys
 * @param {object} BaseGadget
 * @param {object} preferencesManager
 * @param {object} constants
 * @param {object} _utilities
 * @param {object} HBS
 * @param {object} trix
 * @param {object} Overlay
 * @param {object} storageManager
 * @param {object} AnalyticsService
 * @param {object} PAIPConstant
 * @returns Search view
 */
define([
'jquery.plugins',
'features/fitCountriesOverlay/fitCountriesOverlay',
'features/fitCountriesOverlay/fitHelper',
'framework/windowManager',
'framework/gadgetManager',
'framework/messageManager',
'framework/services',
'framework/serviceManager',
'framework/keys',
'gadgets/baseGadget/baseGadget',
'common/constants',
'common/_utilities',
'templates/handlebars-compiled',
'trix',
'framework/storageManager',
'services/analyticsService',
'services/PAIPConstant',
'services/featureFlagService'],
function ($,
fitCountriesOverlay,
fitHelper,
windowManager,
gadgetManager,
messageManager,
services,
serviceManager,
keys,
BaseGadget,
constants,
_utilities,
HBS,
trix,
storageManager,
AnalyticsService,
PAIPConstant,
featureFlagService) {
  'use strict';

  var liveRegion = $('#politeAlertA11y p');
  const COMMA = 44;
  const DOT_CODE = 46;
  const VERTICAL_BAR = 124;

  return $.widget('eti.search', BaseGadget, {
    options: {
      filter: []
    },
    intLastRightPaneWidth: 142,
    currentHighlightPref: '',
    fromSearchH: false,
    fromtaggedlNumber: false,
    fromNoteslNumber: false,
    queryName: '',
    anchorDocIds: null,
    querySource: constants.QUERY_SOURCE.BRS,


    _bindListeners: function () {
      var context = this;

      $('.gadget.search').off('focus change input click keyup ').on('focus change input click keyup ', function () {
        windowManager.getWindow().activeSearch = {
          gadgetId: $(this).data('gadgetid')
        };
      });

      context.element.find('.trix').off('keydown').on('keydown', context._handleSearchTrixKeyDown.bind(this));
      context.element.find('.trix').off('keyup').on('keyup', context._handleSearchTrixKeyUp.bind(this));

      //workaround so HTML is pasted as plain text
      context.element.find('trix-editor')[0].addEventListener('trix-paste', function (data) {
        if (data.pasteData.hasOwnProperty('html')) {
          event.target.editor.undo();
          event.target.editor.insertString(data.pasteData.html);
        }
      });

      context.element.find('.trix').off('click').on('click', function () {
        context.element.find('.trix').focus();

      });

      context.element.find('.trix').off('click', 'a').on('click', 'a', function (e) {
        var searchTrix = context.element.find('trix-editor')[0],
          winSESSION = windowManager.getWindow().SESSION;
        searchTrix.editor.composition.delegate.editor.element.title = '';


        // Find the index of the clicked link
        var childNodes = $(e.target).parent().contents(),
          delStartIndex = 0,
          delEndIndex = 0;

        for (var i = 0; i < childNodes.length; i++) {
          if (e.target === childNodes[i]) {
            break;
          }

          // Disregard comments
          if (childNodes[i].nodeType !== 8) {
            delStartIndex += childNodes[i].length !== undefined ? childNodes[i].length : childNodes[i].innerText.length;
          }
        }

        // Update the end index
        delEndIndex = delStartIndex + $(e.target).text().length;

        searchTrix.editor.setSelectedRange([delStartIndex, delEndIndex]);
        searchTrix.editor.deleteInDirection('backward');

        searchTrix.editor.setSelectedRange([delStartIndex]);

        if (winSESSION.searchHistory && winSESSION.searchHistory.data) {
          $.each(winSESSION.searchHistory.data, function (i, row) {
            var text;
            if ('L' + row.pNumber.toString() + '»' === $(e.target).text().replace(/(?:\r\n|\r|\n)/g, '')) {
              text = _utilities._escapeHtml(row.q.toString());
              searchTrix.editor.insertHTML(_utilities.addParenthesis(text));
              return false;
            }
          });
        }

        context.element.find('.trix').trigger($.Event('keyup', {
          which: keys.SPACE
        }));
      });

      context.element.find('.buttonSubmit').off('click').on('click', function () {
        context.element.find('.trix').trigger($.Event('keyup', {
          which: keys.SPACE
        }));
        AnalyticsService.trackAction(PAIPConstant.ACTION_USER_CLICK_SEARCH, {
          text: context.getSmartSearchValue(context.getTrixSearchText())
        });
        context._handleSearchSubmit(constants.SEARCH_TYPE_SEARCH);
      });

      context.element.find('.titleBar .icon').off('keydown.tabtitlebar').on('keydown.tabtitlebar', context._handleSearchTabDatabases.bind(this));
      context.element.find('.buttonReset').off('click').on('click', context._handleSearchReset.bind(this));

      context.element.find('.trix').off('paste').on('paste', context._handleSearchTrixPasteAndCut.bind(this));

      context.element.find('.trix').off('cut').on('cut', context._handleSearchTrixPasteAndCut.bind(this));


      context.element.find('.trix').off('mouseleave').on('mouseleave', context._handleSearchTrixMouseUpAndMouseLeave.bind(this)); //issue exists when selecting 1st term in search from right to left


      context.element.find('.trix').off('mouseup').on('mouseup', context._handleSearchTrixMouseUpAndMouseLeave.bind(this));
      context.element.find('.titleBar .icon').off('click').on('click', context._handleToggler.bind(this));

      //announce value of trix editor input to screen reader
      context.element.find('#search-faux-edit').off('focus').on('focus', context._trixValueHelper.bind(this));

      context.element.find('.dataCollectionGroup').off('click keydown.tabdatabase', 'label input[type=checkbox]').
      on('click keydown.tabdatabase', 'label input[type=checkbox]', context._handleDatabaseCheck.bind(this));

      //watch for last database checkbox to be focused
      context.element.find('.dataCollection input').off('keydown').on('keydown', context._handleLastDBCheck.bind(this));

      context.element.find('.trix').off('contextmenu', 'a.trix-spelling-highlight').on('contextmenu', 'a.trix-spelling-highlight', context._handleSpellcheck.bind(this));
      context.element.find('.trix').off('mousedown', 'a.trix-spelling-highlight').on('mousedown', 'a.trix-spelling-highlight', context._disableTrixCursorMove.bind(this));

      context.element.find('.showErrorChkBox').off('click').on('click', context._handleShowSearchSyntaxError.bind(this));

      context.element.find('.pluralsChkBox').off('click').on('click', context._handlePluralsChkBox.bind(this));
      context.element.find('.britishEquivalentsChkBox').off('click').on('click', context._handleBritishEquivalentsChkBox.bind(this));
      context.element.find('.queryHighlights').off('change').on('change', context._handleQueryHighlights.bind(this));

      context.$leftPane.resizable({
        minWidth: 309,
        handles: 'e',
        resize: function () {
          context._handleResize();
        },
        start: function (event, ui) {
          ui.originalSize.width = $(this).width();
          context.intLastRightPaneWidth = context.element.parent().width() - ui.originalSize.width;
        },
        stop: function (event, ui) {
          ui.originalSize.width = $(this).width();
          context.intLastRightPaneWidth = context.element.parent().width() - ui.originalSize.width;

        }
      });

      context.element.find('.operator').off('change').on('change', context._handleOperator.bind(this));

      //handle tabbing on 'search' button to go back to search input vice search results gadget
      context.element.find('.buttonSubmit').off('keydown').on('keydown', context._handleSearchTab.bind(this));

      //handle tabbing on 'clear' button
      context.element.find('.buttonReset').off('keydown').on('keydown', context._handleSearchClearBtnTab.bind(this));

      context.element.find('.allDBs').off('change');
      context.element.find('.allDBs').on('change', function () {
        context.element.find('.dataCollectionGroup input').prop('checked', $(this).prop('checked'));
        context._saveSearchSession();
      });

      context.element.find('.dataCollectionGroup input').off('change');
      context.element.find('.dataCollectionGroup input').on('change', function () {
        if (false === $(this).prop('checked')) {
          context.element.find('.allDBs').prop('checked', false);
        }
        if (context.element.find('.dataCollectionGroup input:checked').length === context.element.find('.dataCollectionGroup input').length) {
          context.element.find('.allDBs').prop('checked', true);
        } else {
          context.element.find('.allDBs').prop('checked', false);
        }
        context._saveSearchSession();
      });

      context.element.find('.buttonToggle').off('click').on('click', function (e) {
        e.stopImmediatePropagation();
        var isOpenOrClosed = parseInt($(e.currentTarget).data('state'));
        _utilities._expandGadgetMenu(e, isOpenOrClosed, context);
        $(e.currentTarget).data('state', isOpenOrClosed === 0 ? ++isOpenOrClosed : --isOpenOrClosed);
        context._handleToggleOptions(e, isOpenOrClosed);
      });

      context.element.find('.searchBottomButtons p').off('click').on('click', function (e) {
        context.element.find('.buttonToggle').click();
      });

      context.element.
      find('.buttonPN').
      off('click').
      on('click', function () {
        let searchText = context.getTrixSearchText();

        searchText = _utilities.addParenthesis(searchText);
        searchText = searchText + '.pn.';
        const searchTrixEditor = context.element.find('trix-editor')[0].editor;
        context._emptyTrixEditor();
        searchTrixEditor.insertHTML(searchText);

        context.element.find('.trix').trigger(
          $.Event('keyup', {
            which: 0
          })
        );
        AnalyticsService.trackAction(PAIPConstant.ACTION_USER_CLICK_PN, {
          text: context.getSmartSearchValue(context.getTrixSearchText())
        });
        context._handleSearchSubmit(constants.SEARCH_TYPE_PN);
      });

      context.element.
      find('.dataCollectionGroup').
      off('click', '.btn-FIT-launch').
      on('click', '.btn-FIT-launch', context._handleFitCountriesOverlay.bind(this));
    },

    _handleFitCountriesOverlay: function (e) {
      var strCurrentSearchGadget = 'search_' + this.options.data.gadgetId;
      fitCountriesOverlay.show('fitCountriesOverlay', e, strCurrentSearchGadget, 'search');
      fitCountriesOverlay.applyCallback = this._handleFITapply.bind(this);
    },

    _handleFITapply: function (checkedFitCountries) {
      fitHelper.setFitCountriesToSession(checkedFitCountries, this);
    },

    _resize: function () {
      var context = this;
      var intHeight = context.$panel.height() - context.$tabcontrols.outerHeight() - 1,
        intAllowedMinimumWidth = 485,
        intGadgetWidth = context.element.parent().width(),
        intLeftPaneWidth;

      intLeftPaneWidth = intGadgetWidth - this.intLastRightPaneWidth;

      //elements
      var searchSplitter = context.element.find('.searchSplitter'),
        searchBottom = context.element.find('.searchBottom'),
        searchError = context.element.find('.searchError');

      context.element.height(intHeight);
      context.element.find('.container').height(intHeight);
      $(searchSplitter).height(intHeight);

      if (intGadgetWidth > 485 && context.$rightPane.hasClass('automatic')) {
        context.$rightPane.removeClass('automatic collapse');
        context.element.find('.titleBar .icon').attr({
          'title': 'Collapse',
          'aria-expanded': 'true'
        }).children('.sr-only').html('Collapse Search Options');

        this.intLastRightPaneWidth = intGadgetWidth - intLeftPaneWidth;
      }

      if (this.$rightPane.hasClass('collapse')) {
        intAllowedMinimumWidth = 338;
      }
      if (intGadgetWidth > intAllowedMinimumWidth) {

        if (!this.$rightPane.hasClass('collapse')) {
          this.$leftPane.width(intGadgetWidth - this.intLastRightPaneWidth);
          this.$rightPane.width(this.intLastRightPaneWidth);
        } else {
          this.$leftPane.width(intGadgetWidth - 28);
        }

      } else {
        if (!this.$rightPane.hasClass('collapse')) {
          this.$rightPane.addClass('automatic');
          this.element.find('.titleBar .icon').click();
        }
      }

      //check if the bottom is in one row or two and then add max-height
      var seachBottomHeight = $(searchBottom).height();
      $(searchError).css('bottom', seachBottomHeight + 'px');
      context._setTrixHeight();
    },

    _setTrixHeight: function () {
      var context = this,
        trixHeight,
        intHeight = context.$panel.height() - context.$tabcontrols.outerHeight() - 1,
        searchBottom = context.element.find('.searchBottom'),
        searchError = context.element.find('.searchError'),
        searchDBtitleBar = context.element.find('.titleBar');

      if (searchError.is(":hidden")) {
        trixHeight = context.$leftPane.height() - searchBottom.outerHeight();
      } else {
        trixHeight = context.$leftPane.height() - searchError.outerHeight() - searchBottom.outerHeight();
      }

      context.element.find('trix-editor').height(trixHeight - 25);
      context.element.find('.searchContainer').css('max-height', trixHeight + 'px');
      context.element.find('.dataCollectionHolder').height(intHeight - searchDBtitleBar.outerHeight());
    },

    _create: function () {
      this._super(true);
      this._loadLayoutPreferences();
    },

    _loadLayoutPreferences: function () {
      const context = this;
      let fitElement;

      context._getDefaultLayoutPreferences().done(function () {
        context._renderLayout();
        context._restoreSearchSession();
        context._bindListeners();
        context._openCloseOptionsArea();
        context._resize();

        //remove and add back fit checkbox in DB selection
        context.fitFeatureSub = featureFlagService.subscribeToFitFeature((value) => {
          const container = context.element.find('.dataCollectionGroup');
          if (value) {
            if (fitElement) {
              container.append(fitElement);
              fitElement = null;
              context.element.find('.featureFlagFit input').prop('checked', true);
            }
          } else {var _container$find;
            if (((_container$find = container.find('.featureFlagFit')) === null || _container$find === void 0 ? void 0 : _container$find.length) > 0) {
              context.element.find('.featureFlagFit input').prop('checked', false);
              fitElement = container.find('.featureFlagFit').detach();
            }
          }
          //Update the 'select all' checkbox after toggle.
          if (context.element.find('.dataCollectionGroup input:checked').length === context.element.find('.dataCollectionGroup input').length) {
            context.element.find('.allDBs').prop('checked', true);
          } else {
            context.element.find('.allDBs').prop('checked', false);
          }
        });
      });
    },

    _openCloseOptionsArea: function () {
      var context = this;
      if (context.layoutPreferences && context.layoutPreferences.optionsExpand === 'expanded') {
        context.element.find('.leftPane .buttonToggle').click();
      }
    },

    _renderLayout: function () {
      const strTemplateHtml = HBS['gadgets/search/search']({
        gadgetId: $(this.element).data('gadgetid')
      });
      this.element.html(strTemplateHtml);
      this.$panel = this.element.closest('.panel');
      this.$tabcontrols = this.$panel.find('.tabcontrols');
      this.$rightPane = this.element.find('.rightPane');
      this.$leftPane = this.element.find('.leftPane');
      this._renderDefaultLayout();
    },

    _renderDefaultLayout: function () {
      const context = this;

      if (context.layoutPreferences.showDbs) {
        this.element.find('.collapse').show();
      }
      this.element.find('.operator').val(context.layoutPreferences.operator);
      this.element.find('.showErrorChkBox').prop('checked', context.layoutPreferences.showErrorChkBox);
      this.element.find('.pluralsChkBox').prop('checked', context.layoutPreferences.pluralsChkBox);
      this.element.find('.britishEquivalentsChkBox').prop('checked', context.layoutPreferences.britishEquivalentsChkBox);
      if (context.layoutPreferences.showSearchError) {
        this.element.find('.searchError').show();
      }
      this.element.find('.queryHighlights').val(context.layoutPreferences.queryHighlights);
      context.element.find('input[name="collections"]').map(function () {
        var objName = $(this).val();
        var usDBs = context.layoutPreferences.dbs;
        var found = usDBs.find((dbSource) => dbSource.toUpperCase() === objName.toUpperCase()) !== undefined;
        if (found) {
          context.element.find('input[value="' + objName + '"]').prop('checked', true);
        } else {
          context.element.find('input[value="' + objName + '"]').prop('checked', false);
        }
      });

      const searchGadgetId = 'search_' + this.options.data.gadgetId;
      if (fitHelper.getFitCountriesFromSession(searchGadgetId)) {
        fitHelper.setFitCountriesToSession(fitHelper.getFitCountriesFromSession(searchGadgetId), context);
      } else {
        fitHelper.setFitCountriesToSession(fitHelper.getSelectedFitCountryCodes(searchGadgetId), context);
      }
      if (this.element.find('.dataCollectionGroup input:checked').length === this.element.find('.dataCollectionGroup input').length) {
        this.element.find('.allDBs').prop('checked', true);
      } else {
        this.element.find('.allDBs').prop('checked', false);
      }
      const strSearchText = this.element.find('.trix').val();
      this._enableDisableButtons(strSearchText);
    },

    _saveSearchSession: function () {
      var strCurrentSearchGadget = 'search_' + this.options.data.gadgetId,
        strSearchText = this.element.find('.trix').val(),
        strOperator = this.element.find('.operator').val(),
        strShowError = this.element.find('.showErrorChkBox').prop('checked'),
        strPlurals = this.element.find('.pluralsChkBox').prop('checked'),
        strShowHighlights = this.element.find('.queryHighlights').val(),
        strBritishEquivalents = this.element.find('.britishEquivalentsChkBox').prop('checked'),
        strAllDbs = this.element.find('.allDBs').prop('checked'),
        arrDatabases = this.element.find('input[name="collections"]:checked').map(function () {
          return $(this).val();
        }).get();

      let fitCountries = fitHelper.getFitCountriesFromSession(strCurrentSearchGadget);
      windowManager.getWindow().SESSION.search = windowManager.getWindow().SESSION.search || {};
      windowManager.getWindow().SESSION.search[strCurrentSearchGadget] = {
        searchText: strSearchText,
        operator: strOperator,
        showError: strShowError,
        searchPlurals: strPlurals,
        searchBritishEquivalents: strBritishEquivalents,
        showHighlights: strShowHighlights,
        allDbs: strAllDbs,
        databases: arrDatabases,
        fitCountries: fitCountries
      };
    },

    _restoreSearchSession: function () {
      var context = this,
        strCurrentSearchGadget = 'search_' + context.options.data.gadgetId,
        strSearchText,
        strOperator,
        strShowError,
        strPlurals,
        strBritishEquivalents,
        strShowHighlights,
        strAllDbs,
        arrDatabases = [],
        arryCheckedFitCountries = [];

      const currentSession = windowManager.getWindow().SESSION && windowManager.getWindow().SESSION.search && windowManager.getWindow().SESSION.search[strCurrentSearchGadget];


      if (currentSession && currentSession.hasOwnProperty('searchText') && currentSession.hasOwnProperty('databases')) {
        strSearchText = currentSession.searchText;
        strOperator = currentSession.operator;
        strShowError = currentSession.showError;
        strPlurals = currentSession.searchPlurals;
        strBritishEquivalents = currentSession.searchBritishEquivalents;
        strShowHighlights = currentSession.showHighlights;
        strAllDbs = currentSession.allDbs;
        arrDatabases = currentSession.databases;
        arryCheckedFitCountries = currentSession.fitCountries;

        fitHelper.setFitCountriesToSession(arryCheckedFitCountries, context);
        context.element.find('.allDBs').prop('checked', strAllDbs);
        context.element.find('.trix').val(strSearchText);
        context.element.find('.operator').val(strOperator);
        context.element.find('.showErrorChkBox').prop('checked', strShowError);
        context.element.find('.pluralsChkBox').prop('checked', strPlurals);
        context.element.find('.britishEquivalentsChkBox').prop('checked', strBritishEquivalents);
        context.element.find('.queryHighlights').val(strShowHighlights);

        context.element.find('.dataCollectionGroup input').prop('checked', false);
        arrDatabases.forEach(function (val) {
          context.element.find('label input[value="' + val + '"]').prop('checked', true);
        });

        context._handleShowSearchSyntaxError();

        context._enableDisableButtons(strSearchText);


      }
    },
    _clearSearchSession: function () {
      var strCurrentSearchGadget = 'search_' + this.options.data.gadgetId;
      var sSession = windowManager.getWindow().SESSION.search;
      if (sSession) {
        delete sSession[strCurrentSearchGadget];
        delete sSession.queryId;
      }
    },

    _triggerExternalSearch: function (messageResponse) {
      const context = this;
      context.options.searchText = messageResponse.q;
      //reset SQG to default
      context.element.find('.buttonReset').trigger('click');

      context.element.find('.searchTypePriorArt').prop('checked', true);
      context.element.find('input[name="collections"]').prop('checked', false);
      context.element.find('.allDBs').prop('checked', false);
      context.element.find('.queryHighlights').val(windowManager.getWindow().userPreferences.hitTermHighLightColorOption);

      messageResponse.db.forEach(function (val) {
        context.element.find('label input[value="' + val + '"]').prop('checked', true);
      });

      context._saveSearchSession();
      context._handleSearchSubmit(constants.SEARCH_TYPE_SEARCH, undefined, true);
    },

    _updateSearchGadgetForExternalQuery: function (query) {
      const context = this;
      const searchTrixInput = context.element.find('trix-editor')[0];
      searchTrixInput.editor.insertHTML(query.q);

      context.element.find('.trix').trigger(
        $.Event('keyup', {
          which: keys.SPACE
        })
      );
    },

    _receiveMessage: function (e) {
      var context = this,
        message = e.message,
        messageResponse = e.message.options;

      var displayText = '',
        searchTrixInput;

      switch (message.action) {

        case 'MESSAGE-search-externalQueryUpdate':
          if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
            context._updateSearchGadgetForExternalQuery(messageResponse);
          }
          break;


        case 'MESSAGE-external-search-trigger':
          if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
            context._emptyTrixEditor();
            context._triggerExternalSearch(messageResponse);
            delete windowManager.getWindow().extSearchParams;
          }
          break;
        case 'MESSAGE-search-enable-search-buttons':
          context._enableDisableButtons('x');
          if (message.data === 'search') {
            context.element.find('#search-btn-search').prop('disabled', 'disabled');
            context.element.find('#search-btn-search').addClass('buttonDisabled');
          }
          break;
        case 'MESSAGE-search-disable-search-buttons':
          context._enableDisableButtons('');
          break;
        case 'MESSAGE-searchResults-data':

          // Blur out of search trix programatically since its not blurred out properly when the focus is set to the results
          // Trix bug fix, focusing this way because unless another input gets focus,
          // the trix will keep stealing keystrokes
          // https://github.com/basecamp/trix/issues/172 - issue addressed with no comments
          // remove this once this issue is resolved on the trix side
          // this is related to US21837
          setTimeout(function () {
            // capture the focused element after search results are returned
            // this focused element is being focused by grid/tile views
            //var focusedElement = $(':focus');

            // set a quick focus to the filter input so trix loses its focus properly
            context.element.find('.trix').focus();
            //                        context._selectText();
            // then focus back to the previously focused element to not cause with other focused areas
            //focusedElement.focus();
          }, 100);

          if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
            // Clean the spellcheck errors when the user gets new results
            context.removeSpellcheckStyles();

            // If the search results data is performed, call the spellcheck handler
            if (windowManager.getWindow().SESSION.spellCheckResults && windowManager.getWindow().SESSION.spellCheckResults.length > 0) {
              context._handleTrixSpellcheck(windowManager.getWindow().SESSION.spellCheckResults);
            }
          }

          break;
        case 'MESSAGE-gadget-loaded':
          //set focus to the trix editor in the gadget being opened now.
          if (message.options.script === context.options.script) {
            let currentGadgetId = context.options.data.gadgetId;
            if (message.options.data.gadgetId === currentGadgetId) {
              let element = this.element.find('trix-editor')[0];
              $(element).focus();
              windowManager.getWindow().activeSearch = {
                gadgetId: currentGadgetId
              };
            }
          }
          break;
        case 'MESSAGE-gadget-activated':
          //set focus to the trix editor in the gadget being opened now.
          if (message.options.script === context.options.script) {
            let currentGadgetId = context.options.data.gadgetId;
            if (message.options.data.gadgetId === currentGadgetId) {
              let element = this.element.find('trix-editor')[0];
              $(element).focus();
              windowManager.getWindow().activeSearch = {
                gadgetId: currentGadgetId
              };
              context._resize();
            }
          }
          break;

        case 'MESSAGE-layouts-resetGadgets':
          context.resetGadget();
          break;
        case 'MESSAGE-searchHistory-lNumber':
          this._handleSearchHistoryLNumber(messageResponse);
          break;
        case 'MESSAGE-notesViewer-lNumber':
          this._handleNotesViewerLNumber(messageResponse);
          break;
        case 'MESSAGE-searchHistory-lQuery':
          this._handleSearchHistoryLQuery(messageResponse, e);
          break;
        case 'MESSAGE-taggedDocument-lNumber':
          this._handleTaggedDocumentLNumber(messageResponse);
          break;
        case 'MESSAGE-searchResult-appNumber':
        case 'MESSAGE-taggedDocumentContextMenu-appNumber':
          this._handleContextMenuSelectDocumentsAppNumber(messageResponse);
          break;
        case 'MESSAGE-searchResult-lNumber':
          this._handleContextMenuSelectDocumentsLNumber(messageResponse);
          break;
        case 'MESSAGE-taggedDocumentContextMenu-lNumber':
          this._handleContextMenuSelectDocumentsLNumber(messageResponse);
          break;
        case 'MESSAGE-documentViewer-forward-backward':
          searchTrixInput = this.element.find('trix-editor')[0];
          context._emptyTrixEditor();
          displayText = messageResponse.q;
          context.queryName = messageResponse.queryName + ' ' + this.counter(messageResponse.queryName);
          searchTrixInput.value = displayText;
          var selecteddbs = ['US-PGPUB', 'USPAT', 'USOCR'];
          var sentFromGadget = messageResponse.sentFromGadget,
            buttonClicked = messageResponse.buttonClicked;
          context.selectUnselectDBs(selecteddbs, []);
          context.element.find('.trix').trigger($.Event('keyup', {
            which: keys.SPACE
          }));
          this.element.find('trix-editor').attr('aria-live', 'polite');

          // send forward/backward citation metrics from one place
          // here in the search gadget, where all fbc searches are ultimately executed after user clicks
          let metricName;
          switch (messageResponse.queryName) {
            case constants.FORWARD_CITATION_SEARCH:
              metricName = PAIPConstant.ACTION_FORWARD_CITATION_SEARCH;
              break;
            case constants.BACKWARD_CITATION_SEARCH:
              metricName = PAIPConstant.ACTION_BACKWARD_CITATION_SEARCH;
              break;
            case constants.COMBINED_CITATION_SEARCH:
              metricName = PAIPConstant.ACTION_COMBINED_CITATION_SEARCH;
              break;
            default:
              break;
          }
          if (metricName) {
            // get pn and urpn docs
            let q = messageResponse.q;
            let pnSearchDocs;
            let urpnSearchDocs;
            // check if theres pn docs
            if (q.indexOf('.pn.') >= 0) {
              pnSearchDocs = messageResponse.q.
              substr(0, messageResponse.q.indexOf('.pn.')).
              replace(/\(|\)|\"/g, '').
              split(' | ');
              // check if there are also urpn docs
              if (q.indexOf('.urpn.') >= 0) {
                // urpn docs come AFTER
                urpnSearchDocs = messageResponse.q.
                substr(0, messageResponse.q.indexOf('.urpn.')).
                split(' OR ')[1].
                replace(/\(|\)|\"/g, '').
                split(' | ');
              }
            }
            // else, check if theres urpn docs without pn docs
            else if (q.indexOf('.urpn.') >= 0) {
              urpnSearchDocs = messageResponse.q.
              substr(0, messageResponse.q.indexOf('.urpn.')).
              replace(/\(|\)|\"/g, '').
              split(' | ');
            }

            const metricPayload = {
              originalLNum: _utilities.cleanLNumber(windowManager.getWindow().SESSION.search.lNumber),
              originalQueryId: windowManager.getWindow().SESSION.search.queryId,
              pnSearchDocs,
              urpnSearchDocs
            };
            if (messageResponse.originalDocumentIds) {
              // for backward / combined citation searches, we want to include the docs that were used to derive pnSearchDocs
              metricPayload.originalDocumentIds = messageResponse.originalDocumentIds;
            }
            AnalyticsService.trackAction(metricName, metricPayload);
          } else {
            console.warn('could not determine type of citation search for metrics', messageResponse.queryName);
          }

          context._handleSearchSubmit(constants.SEARCH_TYPE_SEARCH);
          break;

        case 'MESSAGE-documentViewer-searchPatentFamilyID':
          if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
            searchTrixInput = this.element.find('trix-editor')[0];
            var selecteddbs = ['US-PGPUB', 'USPAT', 'USOCR'];
            context._emptyTrixEditor();
            displayText = messageResponse.q;
            context.queryName = messageResponse.queryName;
            searchTrixInput.value = displayText;
            context.selectUnselectDBs(selecteddbs, []);
            context.element.find('.trix').trigger($.Event('keyup', {
              which: keys.SPACE
            }));;
            context._handleSearchSubmit(constants.SEARCH_TYPE_SEARCH);
          }
          break;
        case 'MESSAGE-documentViewer-searchMLTD':
          this._handleMoreLikeThisDocSearch(messageResponse);
          break;
        case 'MESSAGE-imageViewer-grantedPatent':
          this._handleContextMenuSelectDocumentGrantedPatentNumber(messageResponse);
          break;
        case 'MESSAGE-textViewer-grantedPatent':
          this._handleContextMenuSelectDocumentGrantedPatentNumber(messageResponse);
          break;
        default:
          break;
      }
    },

    _handleSearchHistoryLNumber: function (messageResponse) {
      const context = this;

      if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
        let searchTrixInput = this.element.find('trix-editor')[0];
        let displayText;

        context.options.lMatch = {
          'lHistoryNumber': messageResponse.pNumber,
          'lHistoryQuery': messageResponse.q,
          'lHistoryHighlights': messageResponse.highlights,
          'plurals': messageResponse.plurals,
          'lSearchType': messageResponse.searchType,
          'britishEquivalents': messageResponse.britishEquivalents
        };

        if (context.options.lMatch) {
          var pNumPrefix = 'L';


          if (searchTrixInput.value.trim() === '') {
            displayText = pNumPrefix + context.options.lMatch.lHistoryNumber + ' ';
          } else {
            displayText = ' ' + pNumPrefix + context.options.lMatch.lHistoryNumber + ' ';
          }

          searchTrixInput.editor.insertHTML(displayText);

          context.element.find('.trix').trigger($.Event('keyup', {
            which: keys.SPACE
          }));
        }
      }
    },

    _handleSearchHistoryLQuery: function (messageResponse, e) {
      const context = this;

      if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
        context.element.find('input[name="collections"]').prop('checked', false);
        let searchTrixInput = this.element.find('trix-editor')[0];
        context._emptyTrixEditor();

        context.fromSearchH = true;

        // if (messageResponse.buttonType === constants.SEARCH_TYPE_REFRESH) {
        //     context.queryName = messageResponse.queryName;
        // }
        //get anchorDocIDs when query is coming from search History
        if (messageResponse.anchorDocIds) {
          context.anchorDocIds = messageResponse.anchorDocIds;
        }

        if (messageResponse.querySource) {
          context.querySource = messageResponse.querySource;
        }
        // If the querySource is null, set it to BRS
        else {
          context.querySource = constants.QUERY_SOURCE.BRS;
        }
        var dataBaseValue = messageResponse.dbs;

        context.element.find('.allDBs').prop('checked', false);

        if (dataBaseValue.length === $('.dataCollectionGroup input').length) {
          context.element.find('.allDBs').prop('checked', true);
        }

        dataBaseValue.forEach(function (val) {
          context.element.find('label input[value="' + val + '"]').prop('checked', true);
        });

        let displayText = messageResponse.q.replace(/&/g, '&amp;');
        displayText = displayText.replace(/</g, '&lt;');
        displayText = displayText.replace(/>/g, '&gt;');

        searchTrixInput.editor.insertHTML(displayText);
        context.element.find('.operator').val(messageResponse.op);

        context.element.find('.formQueryId').val(messageResponse.queryId);
        context.element.find('.queryHighlights').val(messageResponse.highlights);
        context.element.find('.pluralsChkBox').prop('checked', messageResponse.plurals);
        context.element.find('.britishEquivalentsChkBox').prop('checked', messageResponse.britishEquivalents);
        context.element.find('.trix').trigger($.Event('keyup', {
          which: keys.SPACE
        }));

        context.element.
        find(context.inputNameSearchType).
        filter('[value="' + messageResponse.searchType + '"]').
        prop('checked', true);
        context.element.find('.trix').trigger(
          $.Event('keyup', {
            which: keys.SPACE
          })
        );

        // Update the fit count only if the query has FIT DB selected.
        if (messageResponse.dbs.includes(constants.FIT)) {
          const fitCountries = messageResponse.fitCountries;
          fitHelper.setFitCountriesToSession(fitCountries, context);
        }

        if (messageResponse.buttonType) {
          let excludeResultsAfter = context._getExcludeAfter(messageResponse.buttonType, e.message.options.dateCreated);

          context._handleSearchSubmit(messageResponse.buttonType, excludeResultsAfter);
        }
      }
    },
    /*
    excludeResultsAfter - excludes the results after the original query creation date only when query is re-run using the blue link. Refreshing the query is like a new query run.
    For query refresh, side-by-side - treat the query as new and do not pass the excludeResultsAfter.
    @param buttonType - Type of search : refresh, search, facet, browse(side-by-side).
    @param dateCreated - Original query creation date
    @private
    @memberOf search.js
    */
    _getExcludeAfter: function (buttonType, dateCreated) {
      let excludeTimestamp = [constants.SEARCH_TYPE_REFRESH, constants.SEARCH_TYPE_BROWSE];

      return excludeTimestamp.includes(buttonType) ? null : dateCreated;
    },

    _handleNotesViewerLNumber: function (messageResponse) {
      const context = this;

      if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
        context._emptyTrixEditor();

        // there's currently 2 options for handling l number for NV
        // 1 - clicking the create L# button creates an L number and updates the search gadget
        // 2 - clicking a particular doc id will perform a search without updating the search gadget

        // if this is true.. don't update the search gadget
        if (!messageResponse.clearSearchField) {

          // we have to update the search gadget if this is false
          //toggle on ALL dbs instead of having a list passed in
          context.element.find('input[name="collections"]').prop('checked', true);

          context.element.find('.allDBs').prop('checked', true);


          const searchTrixInput = context.element.find('trix-editor')[0];
          searchTrixInput.editor.insertHTML(messageResponse.q);

          context.element.find('.trix').trigger($.Event('keyup', {
            which: keys.SPACE
          }));
        }

        context.options.searchText = messageResponse.q;
        context.queryName = messageResponse.queryName;

        context.fromNoteslNumber = true;

        // store the patent (coming as message parameter) in the context to be sent to search results gadget
        // This patent will be used to determine, which record in Search Results should be highlighted
        context.currentPatent = messageResponse.currentPatent;

        // Don't persist the query/ L#
        context.ignorePersist = messageResponse.ignorePersist;


        context._handleSearchSubmit(constants.SEARCH_TYPE_SEARCH_HISTORY);

        // Flag determines if search field should be cleared.
        if (messageResponse.clearSearchField) {
          context._emptyTrixEditor();
          context.ignorePersist = null;
        }
      }
    },

    _handleTaggedDocumentLNumber: function (messageResponse) {
      const context = this;

      if (windowManager.getWindow().activeSearch.gadgetId === context.options.data.gadgetId) {
        context._emptyTrixEditor();

        // there's currently 2 options for handling l number for td
        // 1 - clicking the create L# button creates an L number and updates the search gadget
        // 2 - clicking a particular doc id will perform a search without updating the search gadget

        // if this is true.. don't update the search gadget
        if (!messageResponse.clearSearchField) {

          // we have to update the search gadget if this is false
          //toggle on ALL dbs instead of having a list passed in
          context.element.find('input[name="collections"]').prop('checked', true);

          context.element.find('.allDBs').prop('checked', true);

          const searchTrixInput = context.element.find('trix-editor')[0];
          searchTrixInput.editor.insertHTML(messageResponse.q);

          context.element.find('.trix').trigger($.Event('keyup', {
            which: keys.SPACE
          }));
        }

        context.options.searchText = messageResponse.q;
        context.queryName = messageResponse.queryName;

        context.fromtaggedlNumber = true;

        // store the patent (coming as message parameter) in the context to be sent to search results gadget
        // This patent will be used to determine, which record in Search Results should be highlighted
        context.currentPatent = messageResponse.currentPatent;

        // Don't persist the query/ L#
        context.ignorePersist = messageResponse.ignorePersist;

        // add anchor doc ID and query source fields to request
        context.anchorDocIds = messageResponse.anchorDocIds;
        context.querySource = messageResponse.querySource;

        context._handleSearchSubmit(constants.SEARCH_TYPE_SEARCH_HISTORY);

        // Flag determines if search field should be cleared.
        if (messageResponse.clearSearchField) {
          context._emptyTrixEditor();
          context.ignorePersist = null;
        }
      }
    },

    counter: function (queryName) {

      // gadgetManager.openGadgets('searchHistory');
      var data = windowManager.getWindow().SESSION.searchHistory.data;
      if (data) {
        var count = this.matchInArray(data, queryName);
        return count + 1;
      }
      return 1;
    },

    matchInArray: function (data, expression) {
      var len = data.length,
        i = 0,
        count = [];

      // find the query in the array
      for (; i < len; i++) {
        if (data[i].queryName && data[i].queryName.match(expression)) {
          // check if query name is different then q
          if (data[i].queryName.trim() !== data[i].q.trim()) {
            count.push(parseInt(data[i].queryName.replace(expression, '')));
          }
        }
      }
      // get the highest count from all the queries
      if (count.length > 0) {
        count.sort(function (a, b) {return b - a;});
        return count[0];
      } else {
        return 0;
      }
    },
    selectUnselectDBs: function (selectedDbs, unSelectedDbs) {
      var context = this;
      selectedDbs.forEach(function (val) {
        context.element.find('label input[value="' + val + '"]').prop('checked', true);
      });
      unSelectedDbs.forEach(function (val) {
        context.element.find('label input[value="' + val + '"]').prop('checked', false);
      });

      if (context.element.find('.dataCollectionGroup input:checked').length === context.element.find('.dataCollectionGroup input').length) {
        context.element.find('.allDBs').prop('checked', true);
      } else {
        context.element.find('.allDBs').prop('checked', false);
      }
    },
    selectAllDBS: function () {
      var context = this;
      // TODO: delete this temporary implementation for selecting DBS once FIT is available, see TODO: below
      console.warn('temporary implementation: not selecting all dbs for MLTD');
      context.element.find('#US-PGPUB').prop('checked', true);
      context.element.find('#USPAT').prop('checked', true);
      context.element.find('#USOCR').prop('checked', true);
      // TODO: select all including FIT once FIT is implemented for PPUBS, right now this causes 400 bad req from counts api
      // context.element.find('input[name="collections"]').map(function () {
      //     var objName = $(this).val();
      //     context.element.find('input[value="' + objName + '"]').prop('checked', true);
      // });
      // const fitCountries = fitHelper.getAllEnabledCountriesFromFitConfig();
      // fitHelper.setFitCountriesToSession(fitCountries, context);
      // context.element.find('.allDBs').prop('checked', true);

    },
    resetGadget: function () {
      this.element.find('.buttonReset').click();
      this._emptyTrixEditor();
    },

    //Handle message sent by DV gadget to find us more like this document
    _handleMoreLikeThisDocSearch: function (messageResponse) {
      const context = this;
      if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
        let searchTrixInput = this.element.find('trix-editor')[0];

        context._emptyTrixEditor();
        let displayText = messageResponse.q;
        context.queryName = messageResponse.queryName;
        context.anchorDocIds = [messageResponse.anchorId];
        context.querySource = constants.QUERY_SOURCE.MLTD;
        // Check all db
        this.selectAllDBS();

        searchTrixInput.editor.insertHTML(displayText);
        //need this so the text is formatted
        context.element.find('.trix').trigger(
          $.Event('keyup', {
            which: keys.SPACE
          })
        );
        context._handleSearchSubmit(constants.SEARCH_TYPE_SEARCH);
      }
    },

    //Handle message sent by Search Result gadget to find us documents with same application numbers
    _handleContextMenuSelectDocumentsAppNumber: function (messageResponse) {
      const context = this;
      if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
        let searchTrixInput = this.element.find('trix-editor')[0];

        context._emptyTrixEditor();

        context.element.find('.allDBs').prop('checked', false);

        context.element.find('input[name="collections"]').map(function () {
          var objName = $(this).val();
          var usDBs = [constants.USPAT, constants.US_PGPUB, constants.USOCR];
          var found = usDBs.find((dbSource) => dbSource.toUpperCase() === objName.toUpperCase()) != undefined;

          if (found) {
            context.element.find('input[value="' + objName + '"]').prop('checked', true);
          } else {
            context.element.find('input[value="' + objName + '"]').prop('checked', false);
          }
        });


        searchTrixInput.editor.insertHTML(messageResponse.q);

        context.queryName = messageResponse.queryName + ' ' + this.counter(messageResponse.queryName);

        context.element.find('.buttonSubmit').trigger('click');
      }
    },

    //Handle message sent by Search Result gadget to find us documents with same application numbers
    _handleContextMenuSelectDocumentGrantedPatentNumber: function (messageResponse) {
      const context = this;
      if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
        let searchTrixInput = this.element.find('trix-editor')[0];

        context._emptyTrixEditor();

        context.element.find('.allDBs').prop('checked', false);

        context.element.find('input[name="collections"]').map(function () {
          var objName = $(this).val();
          var usDBs = [constants.USPAT, constants.USOCR];
          var found = usDBs.find((dbSource) => dbSource.toUpperCase() === objName.toUpperCase()) !== undefined;

          if (found) {
            context.element.find('input[value="' + objName + '"]').prop('checked', true);
          } else {
            context.element.find('input[value="' + objName + '"]').prop('checked', false);
          }
        });


        searchTrixInput.editor.insertHTML(messageResponse.q);

        context.queryName = messageResponse.queryName + ' ' + this.counter(messageResponse.queryName);

        context.element.find('.buttonBrowse').trigger('click');
      }
    },


    //Handle message sent by Search Result gadget to create L# for selected docs
    _handleContextMenuSelectDocumentsLNumber: function (messageResponse) {
      const context = this;

      if (windowManager.getWindow().activeSearch.gadgetId === this.options.data.gadgetId) {
        let searchTrixInput = this.element.find('trix-editor')[0];

        context._emptyTrixEditor();
        context.element.find('.allDBs').prop('checked', false);
        context.element.find('input[name="collections"]').map(function () {
          var objName = $(this).val();
          var found = messageResponse.uniqueDbSources.find((dbSource) => dbSource.toUpperCase() === objName.toUpperCase()) != undefined;

          if (found) {
            context.element.find('input[value="' + objName + '"]').prop('checked', true);
          } else {
            context.element.find('input[value="' + objName + '"]').prop('checked', false);
          }
        });

        searchTrixInput.editor.insertHTML(messageResponse.q);
        context.queryName = messageResponse.q;

        context.element.find('.trix').trigger($.Event('keyup', {
          which: keys.SPACE
        }));

        context.ignorePersist = messageResponse.ignorePersist;
        this._prepareCountsCallPayload(messageResponse);
      }
    },

    _prepareCountsCallPayload: function (messageResponse) {
      var context = this,
        searchTrix = context.element.find('trix-editor')[0],
        match,
        searchText,
        searchQuery;
      const searchGadgetId = 'search_' + context.options.data.gadgetId;

      var h1_snippets = $('.controls .snippets :selected').val();
      searchQuery = {
        anchorDocIds: context.anchorDocIds,
        querySource: context.querySource,
        caseId: windowManager.getWindow().caseId,
        h1_snippets: h1_snippets,
        q: context.queryName,
        op: context.element.find('#search-or-select').val(),
        queryName: context.queryName,
        qt: "brs",
        highlights: context.element.find('.queryHighlights').val(),
        plurals: context.element.find('.pluralsChkBox').prop('checked'),
        britishEquivalents: context.element.find('.britishEquivalentsChkBox').prop('checked'),
        databaseFilters: [],
        searchType: constants.SEARCH_PRIOR_ART,
        ignorePersist: context.ignorePersist,
        userEnteredQuery: context.getOriginalSearchText(),
        viewName: messageResponse.viewName ? messageResponse.viewName : 'grid'
      };

      messageResponse.uniqueDbSources.forEach(function (item, index) {
        let countryCodes = [];
        if (item.countryCodes) {
          countryCodes = item.countryCodes;
        }
        var databaseFilter = {
          databaseName: item,
          countryCodes
        };
        searchQuery.databaseFilters.push(databaseFilter);
      });

      this._execQueryCounts(searchQuery).done(function (response) {
        messageManager.send({
          action: 'MESSAGE-searchResults-data',
          options: {
            query: response
          }
        });
      });

    },

    _execQueryCounts: function (searchQuery) {
      return serviceManager.exec({
        url: services.getUrl('searchResults.numFound'),
        params: JSON.stringify(searchQuery),
        type: window.CONFIG.mock ? 'GET' : 'POST',
        contentType: 'application/json; charset=UTF-8',
        timeout: 300000,
        notification: false
      });
    },



    _handleDatabaseCheck: function (e) {
      var context = this,
        lastItem,
        databaseArray = context.element.find('input[name="collections"]').map(function () {
          return $(this).val();
        });

      var searchTrixEditor = context.element.find('trix-editor')[0].editor;

      if (context.element.find('.dataCollectionGroup input:checked').length === context.element.find('.dataCollectionGroup input').length) {
        context.element.find('.allDBs').prop('checked', true);
      } else {
        context.element.find('.allDBs').prop('checked', false);
      }

      if (e.which === keys.TAB || e.keyCode === keys.TAB) {
        lastItem = databaseArray[databaseArray.length - 1];
        //check to see if last db check has class active, if it does, skip the following 'if' statement
        var lastItemCheck = $('#' + lastItem).hasClass('last-db-active');
        if (e.target.nextSibling.textContent.trim() === lastItem && !lastItemCheck) {
          context.element.find('.buttonReset').focus();
        }
      }
      context._saveSearchSession();
      context._enableDisableButtons(searchTrixEditor.getDocument().toString());
    },

    _handleSearchTabDatabases: function (e) {
      var context = this;
      context._handleShiftTabRightSearchPanel(e);
      context._saveSearchSession();
    },

    /*Finds last DB input which is active and adds a class to it to denote as last active DB and handles tab/shift+tab key events*/
    _handleLastDBCheck: function (e) {
      var context = this;
      if (!e.shiftKey && e.keyCode === 9) {
        if ($(e.currentTarget).parents('.dataCollection').nextAll('.dataCollection').find('input:enabled').length > 0) {
          context.element.find('.last-db-active').off('keydown').on('keydown', context._handleLastDBCheckTab.bind(this));
        } else {
          context.element.find('#search-or-select').focus();
          context.element.find('#search-or-select').off('keydown').on('keydown', context._handleDefaultOperatorTab.bind(this));
          e.preventDefault();
        }
      }
    },

    /*If user tabs on last active DB, set the focus to the 'or' select element in the search*/
    _handleLastDBCheckTab: function (e) {
      var context = this;
      if (!e.shiftKey && e.keyCode === 9) {

        context.element.find('#search-or-select').focus();
        context.element.find('#search-or-select').off('keydown').on('keydown', context._handleDefaultOperatorTab.bind(this));
        e.preventDefault();

      }
    },

    /*If user uses 'shift+tab' on the 'or' select element in the search, set the focus back to the last active DB checkbox*/
    _handleDefaultOperatorTab: function (e) {
      var context = this,
        expanded = context.element.find('#search-panel-toggle-control').attr('title') === 'Collapse';
      if (e.shiftKey && e.keyCode === 9 && expanded) {
        //using $ in place of 'context.element.find' to resolve JS type error in console
        $('.last-db-active').focus();
        e.preventDefault();
      } else if (e.shiftKey && e.keyCode === 9) {
        context.element.find('#search-panel-toggle-control').focus();
        e.preventDefault();
      }

    },

    /*Handles when user tabs from 'search' button to set focus back to search input*/
    _handleSearchTab: function (e) {
      var context = this;
      if (e.shiftKey && e.keyCode === 9) {

        e.preventDefault();
      } else if (e.keyCode === 9) {
        e.preventDefault();
        var nextZoneExists = context.element.find(e.currentTarget).closest('.zone').nextAll('.zone:visible') ? true : false;
        if (nextZoneExists) {
          //need to correct HTML order to properly handle tabbing.
          context.element.find(e.currentTarget).closest('.zone').nextAll('.zone:visible').find('.tab.active').children('.title').focus();
        } else {
          $('#site-heading').focus();
        }
      }
    },

    /*Handles when user tabs from 'clear' button to follow visual focus*/
    _handleSearchClearBtnTab: function (e) {
      var context = this;

      //if 'clear' button is the only enabled button
      if (e.shiftKey && e.keyCode === 9) {
        return;
      }

      if (e.keyCode === 9) {

        return;

      }
    },
    /**
     * Check if the matched L or N term is an existing query, if so format it.
     * @param {*} match
     */
    _checkIfExistingLSearch: function (match) {
      let winSESSION = windowManager.getWindow().SESSION,
        title = '',
        blnMatchesSearchHistory = false;

      winSESSION.searchHistory.data.forEach((row) => {
        if ('L' + row.pNumber.toString() === match.toUpperCase()) {
          title = row.q.toString();
          blnMatchesSearchHistory = true;
          return false;
        }
      });

      return {
        title: title,
        blnMatchesSearchHistory: blnMatchesSearchHistory
      };
    },
    /**
     * Highlight or format the existing L, N and C numbers in the query.
     * @param {*} e
     * @private
     * @memberof search.js
     */
    _handleSearchCandLHighlight: function (e) {
      const context = this;
      if (e.which === keys.SPACE || e.which === keys.ENTER || e.which === keys.QUOTE) {

        e.preventDefault();
        var cursorPositionReset = false,
          searchTrix = this.element.find('trix-editor')[0],
          pos = searchTrix.editor.getSelectedRange(),
          searchTrixEditor = searchTrix.editor,
          match;

        var offSetPosition = this.removeAnchorStyles(searchTrix);
        var newPos = [pos[0] + offSetPosition, pos[1] + offSetPosition];
        searchTrix.editor.setSelectedRange(pos);
        var searchText = searchTrixEditor.getDocument().toString();

        var reSearchHistory = new RegExp(constants.SEARCH_LOOKBEHIND_IGNORE_SPECIAL_CHARS + '(^|\\b)((c|l|n)\\d+' + constants.SEARCH_LOOKAHEAD_IGNORE_SPECIAL_CHARS + '\\b)', 'gi');
        var blnMatchesSearchHistory = false;

        var newOffsetPosition = 0,
          title = '',
          historyString = '',
          result = {};

        while ((match = reSearchHistory.exec(searchText)) !== null) {
          searchTrix.editor.setSelectedRange([match.index + newOffsetPosition, match.index + match[0].length + newOffsetPosition]);
          historyString = '';

          //check if the term in the query is an existing L# or N#, so format it
          result = context._checkIfExistingLSearch(match[0]);
          blnMatchesSearchHistory = result.blnMatchesSearchHistory;


          title = result.title;

          if (blnMatchesSearchHistory) {
            historyString = '<a href=\'javascript:void(0)\' class=\'trix-highlight\' title=\'' + title.replace(/&/g, '&amp;').replace(/'/g, '&#39;') + '\'>' + match[0].toUpperCase() + '»</a>'; //removing extra white space here
            newOffsetPosition = newOffsetPosition + 1; //'»' 1 char added
            searchTrix.editor.insertHTML(historyString);
          } else {
            historyString = match[0];
            searchTrix.editor.insertString(historyString);
          }
          cursorPositionReset = true;
        }

        if (cursorPositionReset) {
          searchTrix.editor.setSelectedRange(newPos[0] + newOffsetPosition, newPos[1] + newOffsetPosition);
        }
      }
    },

    _handleOperator: function () {
      var context = this;
      var searchTrixEditor = context.element.find('trix-editor')[0].editor;

      context._enableDisableButtons(searchTrixEditor.getDocument().toString());
      context._saveSearchSession();
    },

    _handleToggler: function () {
      var context = this,
        intGadgetWidth = context.element.parent().width(),
        intMinRightPaneWidth = 28,
        intLeftPaneWidth,
        expandStatus;
      if (context.$rightPane.hasClass('collapse')) {
        if (intGadgetWidth > 485) {
          context.$rightPane.removeClass('collapse');
          expandStatus = 'expanded';
          context.element.find('.titleBar .icon').attr({
            'title': 'Collapse',
            'aria-expanded': 'true'
          }).children('.sr-only').html('Collapse Search Options');
          if (context.$rightPane.hasClass('automatic')) {
            context.intLastRightPaneWidth = 138;
          }
          context.$rightPane.width(context.intLastRightPaneWidth).css('min-width', '138px');

          intLeftPaneWidth = intGadgetWidth - context.intLastRightPaneWidth;
          context.$leftPane.width(intLeftPaneWidth);
          context.$rightPane.removeClass('automatic');
        }
      } else {
        intLeftPaneWidth = intGadgetWidth - intMinRightPaneWidth;
        expandStatus = 'collpased';
        context.$leftPane.width(intLeftPaneWidth);
        context.$rightPane.addClass('collapse');
        context.$rightPane.width('25px').css('min-width', '25px');
        context.element.find('.titleBar .icon').attr({
          'title': 'Expand',
          'aria-expanded': 'false'
        }).children('.sr-only').html('Expand Search Options');
      }


      var intHeight = this.$panel.height() - this.$tabcontrols.outerHeight() - 1;
      var seachBottomHeight = context.element.find('.searchBottom').height();
      var searchDBtitleBarHeight = context.element.find('.titleBar').height();
      context.element.find('.searchError').css('bottom', seachBottomHeight + 'px');
      context.element.find('.dataCollectionHolder').height(intHeight - searchDBtitleBarHeight);

      context._setTrixHeight();

      setTimeout(function () {
        liveRegion.text('The search options has ' + expandStatus);
      }, 0);
    },

    _handleResize: function () {
      var context = this,
        intGadgetWidth = context.element.parent().width(),
        intLeftPaneWidth = context.$leftPane.width(),
        intRightPaneWidth = intGadgetWidth - intLeftPaneWidth,
        intMinRightPaneWidth = 28,
        expandStatus;

      if (intRightPaneWidth < 138) {
        expandStatus = 'expanded';
        context.$leftPane.width(intGadgetWidth - intMinRightPaneWidth);
        context.intLastRightPaneWidth = intMinRightPaneWidth;
        context.$rightPane.addClass('automatic collapse');
        context.element.find('.titleBar .icon').attr({
          'title': 'Collapse',
          'aria-expanded': 'true'
        }).children('.sr-only').html('Collapse Search Options');
        context.$rightPane.width('25px').css('min-width', '25px');
      } else {
        context.$rightPane.removeClass('collapse');
        expandStatus = 'collpased';
        context.element.find('.titleBar .icon').attr({
          'title': 'Expand',
          'aria-expanded': 'false'
        }).children('.sr-only').html('Expand Search Options');
        context.intLastRightPaneWidth = intGadgetWidth - intLeftPaneWidth;
        context.$rightPane.width(context.intLastRightPaneWidth).css('min-width', '138px');
      }

      setTimeout(function () {
        liveRegion.text('The search options has ' + expandStatus);
      }, 0);

      //adding max-height for searchContainer
      //check if the bottom is in one row or two and then add max-height
      var intHeight = this.$panel.height() - this.$tabcontrols.outerHeight() - 1;
      var seachBottomHeight = this.element.find('.searchBottom').height();
      var searchMaxheight = 0,
        searchError = this.element.find('.searchError');

      $(searchError).css('bottom', seachBottomHeight + 'px');

      if (seachBottomHeight > 50) {
        searchMaxheight = intHeight - 100 - $(searchError).height();
      } else {
        searchMaxheight = intHeight - 70 - $(searchError).height();
      }

      if (searchMaxheight > 27) {
        this.element.find('.searchContainer').css('max-height', searchMaxheight + 'px');
      }

      var searchDBtitleBarHeight = context.element.find('.titleBar').height();
      context.element.find('.dataCollectionHolder').height(intHeight - searchDBtitleBarHeight);

      context._setTrixHeight();
    },



    _checkInSearchHistory: function (num) {
      var existInSearchHistory = false;
      if (!num || num.indexOf(',') > 0 || num.indexOf('.') > 0) {
        return existInSearchHistory;
      }
      if (windowManager.getWindow().SESSION.searchHistory && windowManager.getWindow().SESSION.searchHistory.data) {
        $.each(windowManager.getWindow().SESSION.searchHistory.data, function (i, row) {
          if (row.pNumber === parseInt(num)) {
            existInSearchHistory = true;
          }
        });
      }
      return existInSearchHistory;
    },
    _editSearchQuery: function () {
      var context = this,
        existInSearchHistory = false,
        searchTrix = context.element.find('trix-editor')[0],
        searchText = searchTrix.editor.getDocument().toString(),
        searchType,
        quotedString,
        tempSearchText,
        add;

      if (searchText !== '' && $.isNumeric(searchText)) {
        var searchString = searchText.toString().trim();


        existInSearchHistory = context._checkInSearchHistory(searchString);

        if (!existInSearchHistory) {
          searchTrix.editor.setSelectedRange([0, searchString.length]);

          quotedString =
          '\"' +
          searchString +
          '\"';

          searchTrix.editor.insertHTML(quotedString);
        }
      } else {
        var matchedIndexes = null,
          matchIndexesRegEx = /(^|(\s))[\d,.]+[.][\S]([^"\s.|,]*)/gi,
          newOffsetPosition = 0;
        while ((matchedIndexes = matchIndexesRegEx.exec(searchText)) !== null && matchedIndexes[0] !== '') {
          if (matchedIndexes[0].match(/[^"\s.|][a-zA-Z]+[0-9]*[^"\s.|]*/gi) !== null && constants.INDICES.indexOf(matchedIndexes[0].match(/[^"\s.|,][a-zA-Z]+[0-9]*[^"\s.|,]*/gi)[0].toLowerCase()) > 0) {
            var numRegEx = /(^|\s)[\d,.]+(?=\.)/gi,
              numMatch;

            while ((numMatch = numRegEx.exec(matchedIndexes[0])) !== null) {
              tempSearchText = searchTrix.editor.getDocument().toString();
              add = 0;

              var num = numMatch[0].toString().trim();

              existInSearchHistory = context._checkInSearchHistory(num);

              if (!existInSearchHistory) {
                if (matchedIndexes[0].substring(0, 1) === ' ') {
                  add = 1;
                }
                newOffsetPosition = tempSearchText.substring(newOffsetPosition, tempSearchText.length).indexOf(matchedIndexes[0]) + add + newOffsetPosition;
                searchTrix.editor.setSelectedRange([newOffsetPosition, num.length + newOffsetPosition]);

                quotedString =
                '\"' +
                num +
                '\"';

                searchTrix.editor.insertHTML(quotedString);
                newOffsetPosition = newOffsetPosition + 2 + num.length;
              }
            }
          }
        }
        searchText = searchTrix.editor.getDocument().toString();
        //DE52154 - quote the unquoted numbers used in range searches.
        context._quoteRangeSearchNumerics(searchTrix);

        //quote the unquoted number terms.
        context._quoteNumerics(searchTrix, existInSearchHistory);

        //match L# in the query
        var regextoMatchL = /(((^|(?=)\s+)|(?<=\()))[L]\d+(?=\s+|(?=\)|$))/gi,
          digit = /[0-9]+/g,
          numericValueMatch,
          lNumber = false,
          numericValue;

        newOffsetPosition = 0;
        searchText = searchTrix.editor.getDocument().toString();
        while ((matchedIndexes = regextoMatchL.exec(searchText)) !== null && matchedIndexes[0] !== '') {
          existInSearchHistory = false;
          numericValueMatch = matchedIndexes[0].toString().trim();
          numericValue = null;

          lNumber = numericValueMatch.substring(0, 1).toUpperCase() === 'L' ? true : false;

          while ((numericValue = digit.exec(numericValueMatch)) !== null && numericValue[0] !== null) {

            if (lNumber) {
              existInSearchHistory = context._checkInSearchHistory(numericValue[0]);
            }

            if (!existInSearchHistory) {
              tempSearchText = searchTrix.editor.getDocument().toString();
              add = 0;

              if (matchedIndexes[0].substring(0, 1) === ' ') {
                add = 1;
              }

              newOffsetPosition = tempSearchText.substring(newOffsetPosition, tempSearchText.length).indexOf(matchedIndexes[0]) + add + newOffsetPosition;
              searchTrix.editor.setSelectedRange([newOffsetPosition, numericValueMatch.length + newOffsetPosition]);

              quotedString =
              '\"' +
              numericValueMatch +
              '\"';

              searchTrix.editor.insertHTML(quotedString);
              newOffsetPosition = newOffsetPosition + 2 + numericValueMatch.length;
            }
          }

        }
      }
    },
    /**
     * Quote the numbers in the query used for range searches irrespective of the number is an existing L/N/C#.
     * Quote the numbers within paranthesis
     * @param {*} searchTrix
     * @param {*} existInSearchHistory
     * @param {*} searchType
     */
    _quoteRangeSearchNumerics: function (searchTrix) {
      let quotedString,
        matchRangesRegEx = /(?:^|\s|\()[@][a-zA-Z]+(?:<[=>]?|=|>=?)([\d]+)/gi,
        newOffsetPosition = 0,
        tempSearchText,
        searchText = searchTrix.editor.getDocument().toString(),
        matchedRanges = matchRangesRegEx.exec(searchText);

      while (matchedRanges && matchedRanges[1] !== '') {
        let matchedRangeVal = matchedRanges[1],
          num = matchedRangeVal.toString().trim();

        tempSearchText = searchTrix.editor.getDocument().toString();
        newOffsetPosition = matchedRanges.index + tempSearchText.substring(matchedRanges.index, tempSearchText.length).indexOf(matchedRangeVal);
        searchTrix.editor.setSelectedRange([newOffsetPosition, num.length + newOffsetPosition]);
        quotedString =
        '\"' +
        num +
        '\"';

        searchTrix.editor.insertHTML(quotedString);

        matchedRanges = matchRangesRegEx.exec(searchTrix.editor.getDocument().toString());
      }
    },

    /**
     * Quote the numbers in the query. If a number is existing in SH, then donot quote.
     * Quote the numbers within paranthesis
     * Quote the numbers with or without commas
     * @param {*} searchTrix
     * @param {*} existInSearchHistory
     * @param {*} searchType
     */
    _quoteNumerics: function (searchTrix, existInSearchHistory) {
      const context = this;
      let quotedString,
        numericValue;
      let regExMatchNumericValue = new RegExp('(^[\\d,.]+(?=\\s+)|^[\\d,.]+(?=$)|' + constants.LOOKBEHIND_SPACE_PARENTHESIS +
      '[\\d.,]+(?=\\s|\\))|(?<=\\s)[\\d,.]+$)(?=([^"]*"[^"]*")*[^"]*$)', 'g');

      let editorState = JSON.stringify(searchTrix.editor),
        parsedEditorState = JSON.parse(editorState),
        document = parsedEditorState.document[0];

      document.text.forEach(function (text) {
        let token = text.string;
        if (token !== '' && token !== '\n') {
          token = token.replace(regExMatchNumericValue, function (match) {
            existInSearchHistory = false;
            numericValue = match.toString().trim();
            quotedString = match;

            if ($.isNumeric(numericValue)) {//fails for numbers with commas.
              existInSearchHistory = context._checkInSearchHistory(numericValue);
            }
            if (!existInSearchHistory) {
              quotedString =
              '\"' +
              match +
              '\"';
            }
            return quotedString;
          });
          text.string = token;
        }

      });

      searchTrix.editor.loadJSON(parsedEditorState);
    },
    _handleSearchTrixKeyDown: function (e) {
      var context = this;
      var code = e.keyCode || e.which;
      if (code === keys.ENTER) {
        e.preventDefault();
        e.stopImmediatePropagation();
      } else {
        context._enableDisableButtons(e.target.editor.getDocument().toString());
      }

      if (e.keyCode === keys.TAB && !e.shiftKey) {
        //setTimeout added to wait for other functions to run after
        setTimeout(function () {
          context.element.find('#search-panel-toggle-control').focus();
          //check for enabled DB checkboxes and apply class to identify
          if (context.element.find('.dataCollection').find('input:enabled').length > 0) {
            context.element.find('.dataCollection').find('input:enabled').last().addClass('last-db-active');
          }
        }, 0);
      }
    },

    _enableDisableButtons: function (searchText) {
      var context = this,
        searchBtn = context.element.find('#search-btn-search');
      //do not disable browse button
      if (searchText && searchText.trim() !== '') {
        context.element.find('#pn-btn-search').prop('disabled', '');
        searchBtn.prop('disabled', '');
        searchBtn.removeClass('buttonDisabled');
      } else {
        context.element.find('#pn-btn-search').prop('disabled', 'disabled');
        searchBtn.prop('disabled', 'disabled');
        searchBtn.addClass('buttonDisabled');
      }
    },

    /*If user is focused on right panel in search gadget on the collapse icon and uses the 'shift+tab' the focus will fall on the search input*/
    _handleShiftTabRightSearchPanel: function (e) {
      var context = this,
        expanded = context.element.find('#search-panel-toggle-control').attr('title') === 'Collapse';

      if (e.shiftKey && e.keyCode === 9) {
        context.element.find('#search-faux-edit').focus();
        e.preventDefault();
      } else if (e.keyCode === 9) {
        context.element.find('#search-or-select').off('keydown').on('keydown', context._handleDefaultOperatorTab.bind(this));
        if (expanded) {
          context.element.find('input.allDBs').focus();
          e.preventDefault();
        } else {
          context.element.find('#search-or-select').focus();
          e.preventDefault();
        }

      }
    },

    _handleSearchTrixKeyUp: function (e) {
      var context = this,
        searchTrixEditor = e.target.editor,
        pos;
      var code = e.keyCode || e.which;
      if (e.keyCode === 37 || e.keyCode === 38 || e.keyCode === 39 || e.keyCode === 40) {
        pos = searchTrixEditor.getSelectedRange();
        context.getCursorPosition(pos);
        if (!e.shiftKey) {
          searchTrixEditor.setSelectedRange(pos);
        }
        return;
      }

      if (code !== keys.CONTROL && code !== keys.SHIFT && code !== keys.ALT) {
        pos = searchTrixEditor.getSelectedRange();
        searchTrixEditor.setSelectedRange(pos);

        if (this.element.find('.showErrorChkBox').prop('checked')) {
          context.displaySearchErrors();
        }
        context.setMatchingParenthesis(pos);
        context.parseAndReplace();
        context._handleSearchCandLHighlight(e);

        if (code === keys.ENTER && e.ctrlKey) {
          searchTrixEditor.insertLineBreak();
        }

        if (e.keyCode === keys.ENTER && !e.ctrlKey) {
          e.preventDefault();
          e.stopPropagation();
          context.element.find('.buttonSubmit').trigger('click');
        } else {
          context._enableDisableButtons(e.target.editor.getDocument().toString());
        }
      }

      context._saveSearchSession();
    },

    _handleSearchTrixPasteAndCut: function (e) {
      var context = this,
        searchTrixEditor = context.element.find('trix-editor')[0].editor;

      context.displaySearchErrors();
      context.setMatchingParenthesis(searchTrixEditor.getSelectedRange());
      //pass resetcursorposition
      context.parseAndReplace(true);
      context._handleSearchCandLHighlight(e);
      context._enableDisableButtons(searchTrixEditor.getDocument().toString());

      context._saveSearchSession();
    },

    _handleSearchTrixMouseUpAndMouseLeave: function () {
      var context = this,
        searchTrixEditor = context.element.find('trix-editor')[0].editor;

      setTimeout(function () {
        var pos = searchTrixEditor.getSelectedRange();
        //mouse double click not setting the range (issue not there for last term in search string)
        if (pos[0] != pos[1] && searchTrixEditor.getDocument().toString().substring(pos[1] - 1, pos[1]) === ' ') {
          pos[1] = pos[1] - 1;
        }
        context.displaySearchErrors();
        searchTrixEditor.setSelectedRange(pos);
        context.setMatchingParenthesis(pos);
      }, 200);
    },

    _renderError: function (err) {
      console.error(err);
    },

    _selectText: function () {
      var context = this;
      var el = context.element.find('.trix div')[0];
      var doc = document;
      var range;

      if (doc.body.createTextRange) {
        range = doc.body.createTextRange();
        range.moveToElementText(el);
        range.select();
      } else if (window.getSelection) {
        var selection = window.getSelection();
        range = doc.createRange();
        range.selectNodeContents(el);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    },


    _searchPayload: function (searchOptions) {
      const payload = {
        anchorDocIds: null,
        querySource: constants.QUERY_SOURCE.BRS,
        caseId: null,
        h1_snippets: null,
        queryId: null,
        q: '',
        op: null,
        queryName: null,
        qt: 'brs',
        excludeResultsAfter: null,
        highlights: null,
        plurals: null,
        britishEquivalents: null,
        viewName: 'grid',
        databaseFilters: [],
        searchType: null,
        searchOption: null,
        fromtaggedlNumber: null,
        fromNoteslNumber: null,
        currentPatent: null,
        ignorePersist: null,
        userEnteredQuery: null,
        extSearchQueryType: null
      };

      return {
        setAnchorDocIds: function (anchorDocIds) {
          payload.anchorDocIds = anchorDocIds;
        },
        setQuerySource: function (querySource) {
          payload.querySource = querySource;
        },
        setCaseId: function (caseId) {
          payload.caseId = caseId;
        },
        setH1Snippets: function (h1_snippets) {
          payload.h1_snippets = h1_snippets;
        },
        setQueryId: function (queryId) {
          payload.queryId = queryId;
        },
        setQ: function (q) {
          payload.q = q;
        },
        setOp: function (op) {
          payload.op = op;
        },
        setQueryName: function (queryName) {
          payload.queryName = queryName;
        },
        setExcludeResultsAfter: function (excludeResultsAfter) {
          payload.excludeResultsAfter = excludeResultsAfter;
        },
        setHighlights: function (highlights) {
          payload.highlights = highlights;
        },
        setPlurals: function (plurals) {
          payload.plurals = plurals;
        },
        setBritishEquivalents: function (britishEquivalents) {
          payload.britishEquivalents = britishEquivalents;
        },

        setDatabaseFilters: function (databaseFilters) {
          payload.databaseFilters = databaseFilters;
        },
        setSearchType: function (searchType) {
          payload.searchType = searchType;
        },
        setSearchOption: function (searchOption) {
          payload.searchOption = searchOption;
        },
        setFromtaggedlNumber: function (fromtaggedlNumber) {
          payload.fromtaggedlNumber = fromtaggedlNumber;
        },
        setFromNoteslNumber: function (fromNoteslNumber) {
          payload.fromNoteslNumber = fromNoteslNumber;
        },
        setCurrentPatent: function (currentPatent) {
          payload.currentPatent = currentPatent;
        },
        setIgnorePersist: function (ignorePersist) {
          payload.ignorePersist = ignorePersist;
        },
        setUserEnteredQuery: function (userEnteredQuery) {
          payload.userEnteredQuery = userEnteredQuery;
        },
        setExtQueryType: function (extSearchQueryType) {
          payload.extSearchQueryType = extSearchQueryType;
        },
        get: function () {
          return payload;
        }
      };
    },

    /* returns search options based on either search gadget or default preferences*/
    _getSearchOptions: function (usePreferences = false) {
      const context = this;

      const searchOptions = {
        op: usePreferences ? context._getPreferences('searchDefaultOperator') : context.element.find('.operator').val(),
        highlights: usePreferences ? context._getPreferences('hitTermHighLightColorOption') : context.element.find('.queryHighlights').val(),
        plurals: usePreferences ? context._getPreferences('searchPlurals') : context.element.find('.pluralsChkBox').prop('checked'),
        britishEquivalents: usePreferences ? context._getPreferences('searchBritishEquivalents') : context.element.find('.britishEquivalentsChkBox').prop('checked'),
        // the databases is unique
        // if preferences is used, then all databases are set for tagged documents
        // otherwise, selected databases are returned for other searches
        databases: null
      };

      if (usePreferences) {
        searchOptions.databases = windowManager.getWindow().featureFlags['FIT'] ? constants.DATABASES : ['USPAT', 'US-PGPUB', 'USOCR'];
      } else {
        // get checked databases in array form
        const arrDatabases = context.element.
        find('input[name="collections"]:checked').
        map(function () {
          return $(this).val();
        }).
        get();

        searchOptions.databases = arrDatabases;
      }

      return searchOptions;
    },

    _handleSearchSubmit: function (searchButton, excludeResultsAfter, extSearchQueryType) {
      var context = this;

      let usePreferencesForSearchOptions = false;
      // Making SearchHistory gadget active to avoid citation-search feature broken
      $('li.tab.searchHistory').click();
      context._editSearchQuery();

      // by default the search text should be retrieved from the gadget
      let searchText = context.getSmartSearchValue(context.getTrixSearchText());

      // this condition is to set specific scenario for tagged documents and notes viewer related searches
      if (context.fromtaggedlNumber || context.fromNoteslNumber) {
        usePreferencesForSearchOptions = true;

        // if coming from either tagged or notes
        // searchText should be from the options
        // TODO: later... rather than retrieving options from the DOM..
        // whenever the selections change, they should update the model
        searchText = context.options.searchText;
      }

      if (extSearchQueryType) {
        searchText = context.options.searchText;
      }

      if (searchText) {
        context.options.searchText = searchText;

        if (searchText !== '') {
          const h1_snippets = $('.controls .snippets :selected').val();
          const searchOptions = context._getSearchOptions(usePreferencesForSearchOptions);
          const filters = context._getDatabaseFilters(searchOptions.databases);
          const searchPayload = context._searchPayload();

          searchPayload.setAnchorDocIds(context.anchorDocIds);
          searchPayload.setQuerySource(context.querySource);
          searchPayload.setCaseId(windowManager.getWindow().caseId);
          searchPayload.setH1Snippets(h1_snippets);
          searchPayload.setQueryId(context.element.find('.formQueryId').val());
          searchPayload.setQ(searchText);
          searchPayload.setOp(searchOptions.op);
          searchPayload.setQueryName(context.queryName);
          searchPayload.setExcludeResultsAfter(excludeResultsAfter);
          searchPayload.setHighlights(searchOptions.highlights);
          searchPayload.setPlurals(searchOptions.plurals);
          searchPayload.setBritishEquivalents(searchOptions.britishEquivalents);
          searchPayload.setDatabaseFilters(filters.databaseFilters);
          searchPayload.setSearchType(constants.SEARCH_PRIOR_ART);
          searchPayload.setSearchOption(searchButton);
          searchPayload.setFromtaggedlNumber(context.fromtaggedlNumber);
          searchPayload.setFromNoteslNumber(context.fromNoteslNumber);
          searchPayload.setCurrentPatent(context.currentPatent);
          searchPayload.setIgnorePersist(context.ignorePersist);
          let userEnteredQuery = context.getOriginalSearchText() ? context.getOriginalSearchText() : searchText;
          searchPayload.setUserEnteredQuery(userEnteredQuery);
          searchPayload.setExtQueryType(extSearchQueryType);

          if (filters.collections.length) {
            if (searchText === '().did.') {
              searchPayload.setQ('');
            }

            messageManager.send({
              action: 'MESSAGE-search-data',
              options: searchPayload.get()
            });
          }

          if (!windowManager.getWindow().extSearchParams && !context.fromSearchH && !context.fromtaggedlNumber && !context.fromNoteslNumber) {
            context._selectText();
          }

          context._resetFromGadgetFlags();
          context.anchorDocIds = null;
          context.querySource = constants.QUERY_SOURCE.BRS;

          context.queryName = '';
          context.currentPatent = null; //cleanup
        }
      }

      context.element.find('.formQueryId').val('');
      // Setting the SearchResults gadget back to focus
      $('li.tab.searchResults').click();

    },

    _resetFromGadgetFlags: function () {
      const context = this;

      context.fromSearchH = false;
      context.fromtaggedlNumber = false;
      context.fromNoteslNumber = false;
    },

    _getFitCountryCodes: function () {
      const searchGadgetId = 'search_' + this.options.data.gadgetId;

      return fitHelper.getSelectedFitCountryCodes(searchGadgetId);
    },

    _getDatabaseFilters: function (databases) {
      const context = this;


      const filters = {
        collections: [],
        databaseFilters: []
      };

      databases.map(function (item) {
        let countryCodes = [];
        filters.collections.push(item);

        if (item === 'FIT') {
          countryCodes = context._getFitCountryCodes();
          if (!countryCodes || countryCodes.length === 0) {
            return;
          }
        }

        const databaseFilter = {
          databaseName: item,
          countryCodes
        };

        filters.databaseFilters.push(databaseFilter);
      });

      return filters;
    },

    _handlePluralsChkBox: function () {
      var searchTrixEditor = this.element.find('trix-editor')[0].editor;

      this._enableDisableButtons(searchTrixEditor.getDocument().toString());
      this._saveSearchSession();
    },

    _handleBritishEquivalentsChkBox: function () {
      var searchTrixEditor = this.element.find('trix-editor')[0].editor;

      this._enableDisableButtons(searchTrixEditor.getDocument().toString());
      this._saveSearchSession();
    },

    _handleQueryHighlights: function () {
      var searchTrixEditor = this.element.find('trix-editor')[0].editor;

      this._enableDisableButtons(searchTrixEditor.getDocument().toString());
      this._saveSearchSession();
    },



    _handleToggleOptions: function (e, isOpenOrClosed) {
      var status,context = this,
        target = $(e.currentTarget);

      e.stopImmediatePropagation();
      if (target.attr('id') !== 'toggleOptions-btn-search') {
        target = $('#toggleOptions-btn-search');
      }
      if (isOpenOrClosed === 0) {
        status = 'collapsed';
        target.attr({ 'aria-expanded': 'false', 'title': 'Open Search Options' }).focus();
        context.element.find('.buttonToggle').removeClass('collapse');
      } else {
        status = 'expanded';
        target.attr({ 'aria-expanded': 'true', 'title': 'Close Search Options' }).focus();
        context.element.find('.buttonToggle').addClass('collapse');
      }

      liveRegion.text('Search Gadget toggle options menu has ' + status);
      context._resize();

    },

    _handleShowSearchSyntaxError: function () {
      if (this.element.find('.showErrorChkBox').prop('checked')) {
        this.element.find('.searchError').css('display', 'block');
        this.displaySearchErrors();
      } else {
        this.resetSearchErrors();
        this.element.find('.searchError').css('display', 'none');
      }
      this._resize();
      this._saveSearchSession();
    },

    _handleSearchReset: function () {
      this._emptyTrixEditor();
      this.resetSearchErrors();
      this._clearSearchSession();
      this._renderDefaultLayout();
    },

    _emptyTrixEditor: function () {
      var searchTrix = this.element.find('trix-editor')[0];
      if (searchTrix) {
        searchTrix.value = '';
        searchTrix.editor.setSelectedRange(0, 0);
      }
      const strCurrentSearchGadget = 'search_' + this.options.data.gadgetId;
      const currentSession = windowManager.getWindow().SESSION && windowManager.getWindow().SESSION.search && windowManager.getWindow().SESSION.search[strCurrentSearchGadget];
      if (currentSession && currentSession.hasOwnProperty('searchText')) {
        currentSession.searchText = '';
      }
    },

    getOriginalSearchText: function () {
      var searchText = this.getTrixSearchText();
      var len = searchText.length;
      return searchText.substring(0, len - 1);
    },

    getTrixSearchText: function () {
      var searchTrix = this.element.find('trix-editor')[0],
        searchTrixEditor = searchTrix.editor,
        searchText = searchTrixEditor.getDocument().toString();

      return searchText;
    },

    getSmartSearchValue: function (searchText) {
      let formattedValue = searchText;

      formattedValue = formattedValue.replace(/»/g, ''); //replace L# and C# tags
      formattedValue = formattedValue.replace(/\n/g, ' '); //replace new line to empty space
      formattedValue = formattedValue.replace(/  /g, ' '); //replace double space to single space
      formattedValue = formattedValue.replace(/(adj|near|same|and|with|not|or|xor)[(]/gi, '$1 (');
      formattedValue = formattedValue.replace(/[)](adj|near|same|and|with|not|or|xor)/gi, ') $1');
      // replace operators back to caps
      formattedValue = formattedValue.replace(/( adj | near | same | and | with | not | or | xor )/gi, function (v) {return v.toUpperCase();});

      formattedValue = formattedValue.trim(); //trim to remove space at the end or at the start

      return formattedValue;
    },

    // Parse the text field, and handle anything resulting from that.
    parseWidgets: function (cursorPositionReset) {
      var context = this,
        searchTrix = context.element.find('trix-editor')[0],
        pos = searchTrix.editor.getSelectedRange(),
        currentHeight;

      currentHeight = this.element.find('trix-editor').height();

      //get static height such that vertical scroller does not scroll up.
      this.element.find('trix-editor').height(currentHeight);

      // Update the values since the value has changed due to the above loops
      context.removeBlockStyles(searchTrix);

      var searchText = searchTrix.innerHTML,
        builtString = searchText,
        builtStringIndexOffset = 0;

      //set operator regex
      var reOperator = new RegExp('(' + constants.SEARCH_LOOKBEHIND_IGNORE_SPECIAL_CHARS + '(^|\\b)(adj|near|same|with)\\d+' + constants.SEARCH_LOOKAHEAD_IGNORE_SPECIAL_CHARS + '\\b)' +
      '|(' + constants.SEARCH_LOOKBEHIND_IGNORE_SPECIAL_CHARS + '(^|\\b)(adj|near|same|and|with|not|or|xor)(' + constants.SEARCH_LOOKAHEAD_IGNORE_SPECIAL_CHARS + '\\b))', 'gi');
      var match, operatorString;

      while ((match = reOperator.exec(searchText)) !== null) {
        operatorString = '<em>' + match[0] + '</em>';
        builtString = builtString.substr(0, match.index + builtStringIndexOffset) + operatorString + builtString.substr(match.index + match[0].length + builtStringIndexOffset);
        builtStringIndexOffset += 9;
        cursorPositionReset = true;
      }

      if (cursorPositionReset) {
        var currentSb = $(context.element.find('div.searchContainer')).scrollTop();
        context._emptyTrixEditor();
        searchTrix.editor.insertHTML(builtString);
        searchTrix.editor.setSelectedRange(pos);

        var rect = searchTrix.editor.getClientRectAtPosition(pos[0]);

        if (rect) {
          var offset = searchTrix.editor.element.offsetTop,
            offsetParent = searchTrix.editor.element.offsetParent;

          while (offsetParent) {
            offset += offsetParent.offsetTop;
            offsetParent = offsetParent.offsetParent;
          }

          var panel = $(context.element.find('div.searchContainer trix-editor')),
            viewportHeight = panel.height(),
            top = rect.top - offset,
            bottom = rect.bottom - offset;

          if (bottom > viewportHeight) {
            panel.scrollTop(bottom - viewportHeight + currentSb);
          } else if (top < 0) {
            panel.scrollTop(top + currentSb);
          } else {
            panel.scrollTop(currentSb);
          }
        }
      } else {
        searchTrix.editor.setSelectedRange(pos);
      }
    },

    removeParenthesisFormating: function (searchTrix) {
      var b = searchTrix.querySelectorAll('trix-editor strong');
      if (b.length) {
        for (var i = 0; i < b.length; i++) {
          var parent = b[i].parentNode;
          while (b[i].firstChild) {
            parent.insertBefore(b[i].firstChild, b[i]);
          }
          parent.removeChild(b[i]);
        }
        searchTrix.value = searchTrix.innerHTML;
      }
    },

    setMatchingParenthesis: function (pos) {
      var searchTrix = this.element.find('trix-editor')[0],
        cursorLocation = pos[0],
        searchTrixEditor = searchTrix.editor,
        cursorPositionReset = false,
        searchText = searchTrixEditor.getDocument().toString(),
        openParenthesisString = '' + '<strong>' + '(' + '</strong>',
        closeParenthesisString = '' + '<strong>' + ')' + '</strong>';

      this.removeParenthesisFormating(searchTrix);

      searchTrix.editor.setSelectedRange(pos);

      //matching closing parenthesis
      if (searchText[cursorLocation - 1] === ')') {
        //find closing bracket and set color
        var prevPosition = this.getPreviousBracketPosition(searchText, cursorLocation);
        if (prevPosition !== -1 && (prevPosition !== 0 || searchText[0] === '(')) {
          searchTrix.editor.setSelectedRange([prevPosition, prevPosition + 1]);
          searchTrix.editor.insertHTML(openParenthesisString);

          //find closing bracket and set color
          searchTrix.editor.setSelectedRange([cursorLocation - 1, cursorLocation]);
          searchTrix.editor.insertHTML(closeParenthesisString);

          cursorPositionReset = true;
        }
      }

      //matching open parenthesis
      if (searchText[cursorLocation - 1] === '(') {
        var nextPosition = this.getNextBracketPosition(searchText, cursorLocation);
        if (nextPosition !== -1 && (nextPosition !== 0 || searchText[0] === ')')) {
          //find open bracket and set color
          searchTrix.editor.setSelectedRange([cursorLocation - 1, cursorLocation]);
          searchTrix.editor.insertHTML(openParenthesisString);

          //find closing bracket and set color
          searchTrix.editor.setSelectedRange([nextPosition, nextPosition + 1]);
          searchTrix.editor.insertHTML(closeParenthesisString);

          cursorPositionReset = true;
        }

      }

      if (cursorPositionReset) {
        searchTrix.editor.setSelectedRange(pos);
      }

      return true;
    },

    displaySearchErrors: function () {
      var searchTrix = this.element.find('trix-editor')[0],
        searchTrixEditor = searchTrix.editor,
        searchText = searchTrixEditor.getDocument().toString();

      this.resetSearchErrors();
      this.getCursorPosition(searchTrixEditor.getSelectedRange());
      this.getInvalidQuotes(searchText);
      this.getInvalidBrackets(searchText);
      this.getMissingOperatorTerms(searchText);
      this.getInvalidBRSNModifier(searchText);
      this.getStopWords(searchText);
      this.getInvalidIndices(searchText);
    },

    resetSearchErrors: function () {
      var context = this;
      context.element.find('.searchDisplayPos').empty();
      context.element.find('.searchErrorList').empty();

    },

    appendSearchError: function (errMessage) {
      var context = this;
      context.element.find('.searchErrorList').append('<li>' + errMessage + '</li>');
    },



    getCursorPosition: function (pos) {
      if (pos) {
        var startPos = pos[0] + 1;
        var EndPos = pos[1] + 1;
        var displayPosition = 1;
        if (startPos === EndPos) {
          displayPosition = 'Pos ' + startPos;
        } else {
          displayPosition = 'Sel ' + startPos + '...' + EndPos;
        }
        this.element.find('.searchDisplayPos').empty();
        this.element.find('.searchDisplayPos').append('<li>' + displayPosition + '</li>');
      }
    },

    getMissingOperatorTerms: function (searchText) {
      var match;
      var regExp = new RegExp(constants.SEARCH_LOOKBEHIND_IGNORE_SPECIAL_CHARS + '\\b(and|or|adj|near|same|with)' + constants.SEARCH_LOOKAHEAD_IGNORE_SPECIAL_CHARS + '\\b', 'gi');
      var opArray = ['and', 'or', 'adj', 'near', 'same', 'with'];
      var opError = false;

      while ((match = regExp.exec(searchText)) !== null) {
        opError = false;
        if (searchText[match.index - 1] === '(' || match.index === 0 || searchText[match.index + match[0].length] === ')' || match.index + match[0].length + 1 >= searchText.length) {
          opError = true;
        }
        if (!opError) {
          var x = match.index + match[0].length;

          while (x < searchText.length) {
            if (/\s/.test(searchText[x]) || searchText[x] === ')') {
              opError = true;
            } else {
              opError = false;
              break;
            }
            x = x + 1;
          }
        }

        if (!opError) {
          var n = match.index - 1;

          while (n >= 0) {
            if (/\s/.test(searchText[n]) || searchText[n] === '(') {
              opError = true;
            } else {
              opError = false;
              break;
            }
            n = n - 1;
          }
        }

        if (!opError) {
          var searchArray = searchText.split(' ');

          $.each(searchArray, function (i, term) {
            if ($.inArray(term.toLowerCase(), opArray) > -1) {
              if (i - 1 > -1 && $.inArray(searchArray[i - 1].toLowerCase(), opArray) > -1 || i + 1 <= searchArray.length - 1 && $.inArray(searchArray[i + 1].toLowerCase(), opArray) > -1) {
                opError = true;
                return false;
              }
            }
          });
        }

        if (opError) {
          this.appendSearchError(match[0].toUpperCase() + ' at position ' + (match.index + 1) + ' is missing term(s)');
        }
      }

    },

    getInvalidBrackets: function (searchText) {
      //Pos 1: Open parenthesis '(' does not have corresponding close parenthesis ')'
      //Pos 14: Close parenthesis ')' does not have corresponding open parenthesis '('

      // Only attempt to parse if the parenthesis in the input string are
      // balanced.
      if (this.isParensOrderBalanced(searchText)) {
        return true;
      }

      var match, pos;

      var regBrackets = /[\(|\)]/gi;
      while ((match = regBrackets.exec(searchText)) !== null) {
        if (match[0] === '(') {

          pos = this.getNextBracketPosition(searchText, match.index + 1);
          if (pos === -1) {
            this.appendSearchError('Pos ' + (match.index + 1) + ': Mis-matched parenthesis');
          }
        } else if (match[0] === ')') {
          pos = this.getPreviousBracketPosition(searchText, match.index + 1);
          if (pos === -1) {
            this.appendSearchError('Pos ' + (match.index + 1) + ': Mis-matched parenthesis');
          }
        }

      }
    },

    getInvalidQuotes: function (str) {
      //Pos 13: Quote " is not closed
      var quotesCount = (str.match(/\"/gi) || []).length;

      if (!(quotesCount % 2)) {
        return true;
      }

      this.appendSearchError('Pos ' + (str.lastIndexOf('"') + 1) + ': Mis-matched quotes');

    },

    getInvalidBRSNModifier: function (searchText) {
      //"XXXN where N>ZZZ is not a supported operator"
      //set operator regex
      var reOperator = /((^|\b)(same|with|adj|near)(\d+)\b)/gi;
      var match;

      while ((match = reOperator.exec(searchText)) !== null) {
        if (match[0].indexOf('SAME') >= 0 && parseInt(match[0].replace('SAME', ''), 10) > constants.SEARCH_BRS_PROXIMITY_LIMITS.SAME) {
          this.appendSearchError('Pos ' + (match.index + 1) + ': SAMEN where N>' + constants.SEARCH_BRS_PROXIMITY_LIMITS.SAME + ' is not a supported operator');
        }

        if (match[0].indexOf('WITH') >= 0 && parseInt(match[0].replace('WITH', ''), 10) > constants.SEARCH_BRS_PROXIMITY_LIMITS.WITH) {
          this.appendSearchError('Pos ' + (match.index + 1) + ': WITHN where N>' + constants.SEARCH_BRS_PROXIMITY_LIMITS.WITH + ' is not a supported operator');
        }

        if (match[0].indexOf('ADJ') >= 0 && parseInt(match[0].replace('ADJ', ''), 10) > constants.SEARCH_BRS_PROXIMITY_LIMITS.ADJ) {
          this.appendSearchError('Pos ' + (match.index + 1) + ': ADJN where N>' + constants.SEARCH_BRS_PROXIMITY_LIMITS.ADJ + ' is not a supported operator');
        }

        if (match[0].indexOf('NEAR') >= 0 && parseInt(match[0].replace('NEAR', ''), 10) > constants.SEARCH_BRS_PROXIMITY_LIMITS.NEAR) {
          this.appendSearchError('Pos ' + (match.index + 1) + ': NEARN where N>' + constants.SEARCH_BRS_PROXIMITY_LIMITS.NEAR + ' is not a supported operator');
        }
      }
    },

    getStopWords: function (searchText) {
      var reOperator = /(^|[\s\(])(an|are|but|by|for|if|into|is|no|of|on|such|that|the|their|then|there|these|they|this|to|was|will)(?=$|[\s\)])/gi; //end of the line or auto error as you type
      var match;

      var searchTextLen = searchText.length;

      if (searchText.charCodeAt(searchTextLen - 1) === 10 || searchText.charCodeAt(searchTextLen - 1) === 32 || searchText.charCodeAt(searchTextLen - 1) === 160) {
        searchText = searchText.substring(0, searchTextLen - 1);
      }

      while ((match = reOperator.exec(searchText)) !== null) {
        this.appendSearchError('Pos ' + (match.index + 1) + ': \'' + match[0].trim().replace(/\(/g, '').replace(/\)/g, '') + '\' is a stopword and will only be searched in metadata fields');
      }
    },

    getInvalidIndices: function (searchText) {
      var reOperator = /([.|,|\|])[a-zA-Z]*[0-9]*[a-zA-Z]*(?=[.|,|\|])(?!.*([.|,|\|])[a-zA-Z]*[0-9]*[a-zA-Z]*(?=[.|,|\|]))/gi;
      var indicesFwdBkd = /[.][a-zA-Z]*[0-9]*[a-zA-Z]*[.][a-zA-Z]*[0-9]*[a-zA-Z]*/gi;
      var reRangeOperator = /(^|\s|\()[@][\S]([^\)\(=<>"\s]*)/gi;
      var match,rangeMatch,fwdBkdIndiciesMatch,matchSubString,matchLen,indicesArr,matchFound = false,
        context = this;

      // combine special and regular indices
      var strIndicesList = constants.INDICES + constants.SPECIAL_INDICES;

      var searchTextLen = searchText.length;
      if (searchText.charCodeAt(searchTextLen - 1) === 10 || searchText.charCodeAt(searchTextLen - 1) === 32 || searchText.charCodeAt(searchTextLen - 1) === 160) {
        searchText = searchText.substring(0, searchTextLen - 1);
      }
      /*
      const COMMA = 44;
      const DOT_CODE = 46;
      const VERTICAL_BAR = 124;
       */

      //indices list
      // If is within quotes (code 34), it's a search term
      searchText = searchText.trim();

      if (searchText.charCodeAt(0) === 34 && searchText.charCodeAt(searchText.length - 1) === 34) {

        // console.log('valid string');
      } else {
        while ((match = reOperator.exec(searchText)) !== null) {
          matchLen = match[0].length;
          if (match[0].charCodeAt(matchLen - 1) === DOT_CODE || match[0].charCodeAt(matchLen - 1) === COMMA || match[0].charCodeAt(matchLen - 1) === VERTICAL_BAR) {
            matchSubString = match[0].substring(1, matchLen - 1);
          } else {
            matchSubString = match[0].substring(1, matchLen);
          }

          if (!(matchSubString === '.' || matchSubString === ',' || matchSubString === '|') &&
          strIndicesList.indexOf('|' + matchSubString.toLowerCase() + '|') < 0 &&
          constants.SPECIAL_INDICES.indexOf('|' + matchSubString.toLowerCase().substring(0, 4) + '|') < 0) {
            this.appendSearchError('Pos ' + (match.index + 1) + ': \'' + match[0].trim().replace(/\.|,/g, '') + '\' is not a valid index');
          } else {
            if (!(matchSubString === '' || matchSubString === '.' || matchSubString === ',' || matchSubString === '|') && !(searchText.charCodeAt(searchText.indexOf('.' + matchSubString) + matchSubString.length + 1) === 46 || searchText.charCodeAt(searchText.indexOf('.' + matchSubString) + matchSubString.length + 1) === 44 || searchText.charCodeAt(searchText.indexOf('.' + matchSubString) + matchSubString.length + 1) === 124 ||
            searchText.charCodeAt(searchText.indexOf(',' + matchSubString) + matchSubString.length + 1) === 46 || searchText.charCodeAt(searchText.indexOf(',' + matchSubString) + matchSubString.length + 1) === 44 || searchText.charCodeAt(searchText.indexOf(',' + matchSubString) + matchSubString.length + 1) === 124 ||
            searchText.charCodeAt(searchText.indexOf('|' + matchSubString) + matchSubString.length + 1) === 46 || searchText.charCodeAt(searchText.indexOf('|' + matchSubString) + matchSubString.length + 1) === 44 || searchText.charCodeAt(searchText.indexOf('|' + matchSubString) + matchSubString.length + 1) === 124)) {
              this.appendSearchError('Pos ' + (match.index + 1) + ': \'' + match[0].trim().replace(/\.|,/g, '') + '\' has incorrect syntax');
            }
          }
        }
      }

      // if . has indicies forward and backward
      while ((fwdBkdIndiciesMatch = indicesFwdBkd.exec(searchText)) !== null) {
        indicesArr = fwdBkdIndiciesMatch[0].split('.');
        matchFound = false;
        indicesArr.forEach(function (obj, i) {
          if (!matchFound && obj !== '' && strIndicesList.indexOf('|' + obj.toLowerCase() + '|') > 0) {
            matchFound = true;
          } else {
            if (obj !== '' && strIndicesList.indexOf('|' + obj.toLowerCase() + '|') > 0) {
              context.appendSearchError('Pos ' + (fwdBkdIndiciesMatch.index + 1) + ': \'' + fwdBkdIndiciesMatch[0].trim() + '\' has incorrect syntax');
            }
          }
        });
      }

      //indicies @ range list
      while ((rangeMatch = reRangeOperator.exec(searchText)) !== null) {
        //if first character is a (, remove it.  This is to fix the aliases not being grouped when at start of a () group.
        if (rangeMatch[0].startsWith('(')) {
          rangeMatch[0] = rangeMatch[0].substr(1, rangeMatch[0].length);
        }
        //.trim the range match to remove preceding spaces that cause the index not to match
        if (constants.RANGE_INDICES.indexOf('|' + rangeMatch[0].toLowerCase().trim() + '|') < 0) {
          this.appendSearchError('Pos ' + (rangeMatch.index + 1) + ': \'' + rangeMatch[0].trim() + '\' is not a valid index');
        }
      }
    },

    getOnlyBrackets: function (str) {
      var re = /[^()]/g;
      return ('' + str).replace(re, '');
    },

    areBracketsInOrder: function (str) {
      str = '' + str;
      var bracket = {
          ')': '('
        },
        openBrackets = [],
        isClean = true,
        i = 0,
        len = str.length;

      for (; isClean && i < len; i++) {
        if (bracket[str[i]]) {
          isClean = openBrackets.pop() === bracket[str[i]];
        } else {
          openBrackets.push(str[i]);
        }
      }

      return isClean && !openBrackets.length;
    },

    isParensOrderBalanced: function (str) {
      str = this.getOnlyBrackets(str);
      return this.areBracketsInOrder(str);
    },

    getNextBracketPosition: function (str, currentPosition) {
      str = '' + str;
      str = str.replace(/\n/g, ' '); //replace new line to empty space

      var i = 0,
        len = str.length,
        openBracket = '(',
        closeBracket = ')',
        balancedCount = 0,
        pos = -1;

      if (str.indexOf(')') > 0 || str.indexOf('(') > 0) {
        for (i = currentPosition; i < len; i++) {
          if (openBracket === str[i]) {
            balancedCount++;
          }
          if (closeBracket === str[i]) {
            if (balancedCount === 0) {
              pos = i;
              break;
            } else {
              balancedCount--;
            }
          }
        }
      }

      return pos;
    },

    getPreviousBracketPosition: function (str, currentPosition) {
      str = '' + str;

      str = str.replace(/\n/g, ' '); //replace new line to empty space

      var i = 0,
        openBracket = '(',
        closeBracket = ')',
        balancedCount = 0,
        pos = -1;

      if (str.indexOf(')') > 0 || str.indexOf('(') > 0) {
        for (i = currentPosition - 2; i >= 0; i--) {
          if (closeBracket === str[i]) {
            balancedCount++;
          }
          if (openBracket === str[i]) {
            if (balancedCount === 0) {
              pos = i;
              break;
            } else {
              balancedCount--;
            }
          }
        }
      }

      return pos;
    },

    removeBlockStyles: function (searchTrix) {

      var isEmPresent = searchTrix.innerHTML.indexOf('<em>') !== -1;
      if (isEmPresent) {
        searchTrix.value = searchTrix.innerHTML.replace(/<em>/g, '').replace(/<\/em>/g, '');
      }
    },

    removeSpellcheckStyles: function () {
      var searchTrix = this.element.find('trix-editor')[0],
        b = searchTrix.querySelectorAll('trix-editor a.trix-spelling-highlight'),
        originalPos = searchTrix.editor.getSelectedRange();

      if (b.length) {
        for (var i = 0; i < b.length; i++) {
          var parent = b[i].parentNode;
          if (b[i].firstChild) {
            b[i].firstChild.data = b[i].firstChild.data;
            parent.insertBefore(b[i].firstChild, b[i]);
          }
          parent.removeChild(b[i]);
        }
        searchTrix.value = searchTrix.innerHTML;

        // Set the selection back to the original position
        searchTrix.editor.setSelectedRange(originalPos);
      }
    },

    removeAnchorStyles: function (searchTrix) {
      var offSetPosition = 0;
      var b = searchTrix.querySelectorAll('trix-editor a.trix-highlight');
      if (b.length) {
        for (var i = 0; i < b.length; i++) {
          var parent = b[i].parentNode;
          if (b[i].firstChild) {
            var len = b[i].firstChild.data.length;
            if (b[i].firstChild.data.indexOf('»') > 0) {
              b[i].firstChild.data = b[i].firstChild.data.replace('»', '');
              offSetPosition = offSetPosition - 1; //' » ' 2 chars removed
            } else if (b[i].firstChild.data.charCodeAt(len - 1) === 32 || b[i].firstChild.data.charCodeAt(len - 1) === 160) {
              b[i].firstChild.data = b[i].firstChild.data.trim();
              offSetPosition = offSetPosition - 1; //' space ' 1 char removed
            } else if (b[i].firstChild.data.slice(-1) === '»') {
              b[i].firstChild.data = b[i].firstChild.data.replace('»', '');
              offSetPosition = offSetPosition - 1; //' » ' 1 char removed
            }

            parent.insertBefore(b[i].firstChild, b[i]);
          }
          parent.removeChild(b[i]);
        }
        searchTrix.value = searchTrix.innerHTML;
      }
      return offSetPosition;
    },

    parseAndReplace: function (resetCursorPosition) {
      var inputString = this.getSmartSearchValue(this.getTrixSearchText());

      inputString = inputString.replace(/\s+/g, ' ');
      //add space between brakets and text if one is not provided
      inputString = inputString.replace(/[(]/g, ' $1');
      inputString = inputString.replace(/[)]/g, '$1 ');

      this.parseWidgets(resetCursorPosition); // This handles the block level widgets...

      // For now, don't do anything re: replacement if the last character is a space
      if (inputString.substring(inputString.length - 1) === ' ') {
        return false;
      }
    },

    _handleSpellcheck: function (e) {
      // Disable contextmenu
      e.preventDefault();
      if (windowManager.getWindow().SESSION.spellCheckResults && windowManager.getWindow().SESSION.spellCheckResults.length > 0) {
        var context = this,
          misspelledWord,
          childNodes,
          startIndex = 0,
          endIndex = 0;

        // Get the text of the misspelled word
        misspelledWord = $(e.toElement).text();

        // Find the index of the clicked link
        childNodes = $(e.toElement).parent().contents();

        // Loop through all the child nodes
        for (var i = 0; i < childNodes.length; i++) {
          if (e.target === childNodes[i]) {
            break;
          }

          // Disregard comments
          if (childNodes[i].nodeType !== 8) {
            startIndex += childNodes[i].length !== undefined ? childNodes[i].length : childNodes[i].innerText.length;
          }
        }

        endIndex = startIndex + misspelledWord.length;

        // Open the modal on right mouse click
        context._spellcheckOverlay([startIndex, endIndex], misspelledWord);
      }
    },

    // Clean the highlighted word if the user changes it
    _handleSpellcheckKeypress: function (e) {
      var searchTrix = this.element.find('trix-editor')[0],
        originalPos = searchTrix.editor.getSelectedRange(),
        keyCode = e.keyCode || e.which,
        targetWord,
        childNodes,
        startIndex,
        endIndex;

      if (keyCode >= 32 && keyCode <= 255 || keyCode === 8) {
        // Get the text of the misspelled word
        targetWord = $(e.toElement).text();

        // Find the index of the clicked link
        childNodes = $(e.toElement).parent().contents();

        // Loop through all the child nodes
        for (var i = 0; i < childNodes.length; i++) {
          if (e.target === childNodes[i]) {
            break;
          }

          // Disregard comments
          if (childNodes[i].nodeType !== 8) {
            startIndex += childNodes[i].length !== undefined ? childNodes[i].length : childNodes[i].innerText.length;
          }
        }

        // Get the position of the selected word
        endIndex = startIndex + targetWord.length;

        searchTrix.editor.setSelectedRange([startIndex, endIndex]);

        var cleanReplacement = targetWord;

        searchTrix.editor.insertHTML(cleanReplacement);

        // Set the selection back to the original position
        searchTrix.editor.setSelectedRange(originalPos);
      }
    },

    // 'spellcheck' param contains array of objects for misspelled words
    _handleTrixSpellcheck: function (spellcheck) {
      var searchTrix = this.element.find('trix-editor')[0],
        originalPos = searchTrix.editor.getSelectedRange(),
        searchTrixEditor = searchTrix.editor,
        searchText = searchTrixEditor.getDocument().toString(),
        spellcheckTerms = '',
        searchMisspelledTerms,
        match;

      if (spellcheck && spellcheck.length > 0) {

        // make sure token exists
        if (spellcheck[0].hasOwnProperty('token')) {

          // loop over the spellcheck objects to find the misspelled word in trix
          for (var x = 0; x < spellcheck.length; x++) {
            // Only add a separator if its not the first token
            spellcheckTerms += x !== 0 ? '|' : '';
            spellcheckTerms += spellcheck[x].token;
          }

          searchMisspelledTerms = new RegExp('(^|\\b)' + spellcheckTerms + '\\b', 'gi');

          // Only check if the spellcheckterms are not empty
          if (spellcheckTerms !== '' && spellcheckTerms !== null) {
            while ((match = searchMisspelledTerms.exec(searchText)) !== null) {
              searchTrix.editor.setSelectedRange([match.index, match.index + match[0].length]);

              var spellingReplacement = '<a href="javascript:void(0)" class="trix-spelling-highlight">' + match[0] + '</a>';

              searchTrix.editor.insertHTML(spellingReplacement);
            }
          }

          // Set the selection back to the original position
          searchTrix.editor.setSelectedRange(originalPos);
        }
      }
    },

    // Sets up the spellcheck overlay
    _spellcheckOverlay: function (pos, word) {
      var context = this,
        suggestions = [],
        $overlay,
        spellCheckResults,
        correctedWord;

      // get the suggestions based on the word
      if (windowManager.getWindow().SESSION.spellCheckResults && windowManager.getWindow().SESSION.spellCheckResults.length > 0) {
        spellCheckResults = windowManager.getWindow().SESSION.spellCheckResults;

        // loop over the spellcheck objects to find the misspelled word in trix
        for (var x = 0; x < spellCheckResults.length; x++) {
          // if word matches the token, get the suggestions from the object
          if (word.toLowerCase() === spellCheckResults[x].token.toLowerCase()) {
            suggestions = spellCheckResults[x].suggestions;
          }
        }

        // convert to a proper object, since suggestions is a string but trix expects an object
        if (suggestions && suggestions.length > 0) {
          suggestions = suggestions.replace(/\s+/g, '').replace('[', '').replace(']', '').split(',');

          $overlay = $(HBS['gadgets/search/searchSpellcheck']({
            suggestions: suggestions
          }));

          $overlay.appendTo('body');

          context.$overlay = $overlay;

          if (context.$overlay.overlay) {
            context.$overlay.overlay({
              buttonClick: function (e) {
                var strAction = $(e.toElement).attr('data-action');
                if (strAction === 'close') {
                  context._spellcheckOverlayClose();
                }
              }
            });
          }

          // bind event for suggestion click
          context.$overlay.find('ul li[data-indentifier]').off('click').on('click', function () {
            correctedWord = suggestions[$(this).data('indentifier')];

            // close the overlay
            context._spellcheckOverlayClose();

            // call the function to replace the word
            context._replaceMisspellingTrix(pos, correctedWord);
          });
        }
      }
    },

    _replaceMisspellingTrix: function (pos, correctWord) {
      var searchTrix = this.element.find('trix-editor')[0];

      // Set the selector at the position of the word that is being replaced
      searchTrix.editor.setSelectedRange(pos);

      searchTrix.editor.insertHTML(correctWord);

      // Set the selection to the end of the replaced word
      searchTrix.editor.setSelectedRange(pos[0] + correctWord.length);
    },

    _spellcheckOverlayClose: function () {
      var context = this;

      context.$overlay.overlay('instance').close();
    },

    _disableTrixCursorMove: function (e) {
      // Disable cursor from being moved on right click
      if (e && e.which === 3) {
        e.preventDefault();
      }
    },

    //get current value of the trix editor and update the live region to be read by JAWS as the value of trix
    _trixValueHelper: function () {
      var searchTrix = this.element.find('trix-editor')[0],
        liveRegion = this.element.find('#search-input-helper span');

      var currentValue = searchTrix.textContent;

      if (currentValue !== '' && currentValue !== null && currentValue !== undefined) {
        liveRegion.text(currentValue);
      }
    },

    _destroy: function () {
      this.fitFeatureSub.unsubscribe();

      this._super();
    }
  });
});
//# sourceMappingURL=search.js.map
