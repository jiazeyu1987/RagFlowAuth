define([
'jquery.plugins',
'framework/gadgetManager',
'framework/windowManager',
'framework/messageManager',
'gadgets/baseGadget/baseGadget',
'templates/handlebars-compiled',
'framework/services',
'framework/serviceManager',
'framework/logManager',
'widgets/grid/grid',
'common/constants',
'common/_utilities',
'widgets/findWithinWidget/findWithinWidget',
'gadgets/searchResults/searchResultsHelper',
'widgets/advancedFind/advancedFindWidget',
'gadgets/searchResults/searchResultsFindHelper',
'gadgets/searchResults/searchResultsSortHelper',
'gadgets/searchResults/searchResultsGridFormatter',
'gadgets/searchResults/searchResultsCopyDataExtractor',
'gadgets/searchResults/searchResultsMessageHandler',
'gadgets/searchResults/searchResultsGridEventHandler',
'gadgets/searchResults/searchResultsEventHandler',
'features/tagManager/tagManager',
'features/notesManager/notesManager',
'features/navigation/searchResultsManager',
'gadgets/hitTerms/hitTermsHelper',
'gadgets/searchResults/searchResultsGridHelper',
'gadgets/searchResults/searchResultsDataHelper',
'gadgets/searchResults/searchResultsBrowserHelper',
'gadgets/searchResults/searchResultsHittermHelper',
'gadgets/searchResults/searchResultsCreateHelper',
'gadgets/searchResults/searchResultsPreferenceHelper',
'gadgets/searchResults/searchResultsGreyBarHelper',
'gadgets/searchResults/searchResultsPrefetchHelper',
'gadgets/searchResults/searchResultsNoteTagHelper',
'gadgets/searchResults/searchResultsContextMenuConfig',
'gadgets/documentViewer/helper',
'widgets/contextualMenu/contextualMenu',
'services/analyticsService',
'services/PAIPConstant',
'text!gadgets/searchResults/searchResultsPrintCss.css',
'handlebars-helpers'],
function ($,
gadgetManager,
windowManager,
messageManager,
baseGadget,
HBS,
services,
serviceManager,
logManager,
Grid,
constants,
utilities,
findWithinWidget,
searchResultsHelper,
AdvancedFindWidget,
searchResultsFindHelper,
searchResultsSortHelper,
searchResultsGridFormatter,
searchResultsCopyDataExtractor,
searchResultsMessageHandler,
searchResultsGridEventHandler,
searchResultsEventHandler,
tagManager,
notesManager,
searchResultsManager,
hitTermsHelper,
searchResultsGridHelper,
searchResultsDataHelper,
searchResultsBrowserHelper,
searchResultsHittermHelper,
searchResultsCreateHelper,
searchResultsPreferenceHelper,
searchResultsGreyBarHelper,
searchResultsPrefetchHelper,
searchResultsNoteTagHelper,
searchResultsContextMenuConfig,
documentViewerHelper,
ContextualMenu,
AnalyticsService,
PAIPConstant)
{
  'use strict';
  var liveRegion = $('#politeAlertA11y p');
  return $.widget('eti.searchResults', baseGadget, {
    options: {},
    data: {},
    sortingStarted: false,
    isCollectionSearch: false,
    isCollectionSearchData: {},
    gridConfig: [],
    searchQuery: null,
    newSearch: false,
    view: '',
    lNumber: null,
    sortStr: 'score%20desc',
    sorts: {
      ui: [],
      solr: {
        columns: [],
        sortStr: ""
      }
    },
    filters: [],
    overlaySortFilteringStarted: false,
    sortedPatentData: [],
    metaData: {},
    grid: null,
    lastDocId: 0,
    highlight: [],
    ajaxRequest: null,
    singleOrMulti: '',
    slider_update: null,
    highlightClickedRowPage: 0,
    highlightClickedRowHash: {},
    highlightsOff: [],
    lastbuttonClicked: false,
    queryHighlights: null,
    currentPageNumber: 0,
    updateAllHighlightState: {},
    loadedHighlightsForBrowser: false,
    queryId: null,
    fromSearch: false,
    navigateDirection: "",
    summaryXHR: null,
    fetchMore: true,
    defaultCurrentLayoutSort: {},
    cellSelected: false,
    documentWasOpenedMetricFlag: false,

    _resize: function () {
      var intHeight = this.$panel.outerHeight() - this.$tabcontrols.outerHeight() - 1;

      searchResultsHittermHelper.setHighlightBar(this.element);

      this.$container.height(intHeight);
      this.$content.height(intHeight - this.$header.outerHeight());

      this.$content.find('.grid').height(intHeight - this.$header.outerHeight());
      this.$content.find('.slickgrid').height(intHeight - this.$header.outerHeight());

      if (this.grid && this.grid.options) {
        this.grid.options.grid.resizeCanvas();
      }

      if (this.element.find('.slick-header').is(':visible')) {
        this.$content.find('.slick-viewport').height(intHeight - this.$header.outerHeight() - this.element.find('.slick-header').outerHeight());
      } else {
        this.$content.find('.slick-viewport').height(intHeight - this.$header.outerHeight());
      }
    },


    _destroy: function () {
      const context = this;
      searchResultsManager.cancelAjaxCalls(context);
      if (context.storeUnsubscribe) context.storeUnsubscribe();

      context.unbindListeners();

      context.element.find('.contentgrid').off('click', '.btn-new-tab');
      context.element.find('.controls').off('click', '.advancedFind');
      context.element.find('.contentgrid').off('keydown', '.grid');
      context.element.find('.contentgrid').off('keyup', '.grid');
      context.element.parents('.panel').find('.tabcontrols .searchResults').off('keyup');
      context.element.off('column-change', '.grid');
      context.element.find('.controls').off('change', '.filterInput');
      context.element.find('.controls').off('keyup', '.filterInput');
      context.element.find('.searchBox .icon').off('click');
      context.$header.off('click', '.searchSettings');
      context.element.find('.meta-data-settings').off('click', '.close');
      context.element.find('.meta-data-settings').off('keyup', '.close');
      context.element.off('click', '.knob.fontSize');
      context.element.find('.controls').off('click', '.highlightInfo .highlighter');
      context.element.find('.meta-data-settings').off('change', '.setting-menu-options input');
      context.element.find('.moreButton').off('click');
      context.element.find('.resultInfo .page-number .btn-next').off('click');
      context.element.find('.resultInfo .page-number .btn-prev').off('click');
      context.element.off('viewport-changed', '.grid');
      context.element.off('keyup');

      context.element.find('.grid').off('keydown', '.slick-header .slick-header-column');
      context.element.find('.grid').off('resetconfig');
      context.element.find('.grid').off('click', '.slick-row .slick-cell .btn-add-print');
      context.element.find('.contentgrid').off('keyup', '.col-family-group .toggle');
      $(document).off('contextualMenu-item-clicked.' + context.contextMenuColumn.eventNamespace);
      context.element.find('.contentgrid').off('contextmenu', '.grid-canvas');
      context.element.find('.knobs').off('click', '.knob.print');
      context.element.find('.grid').off('custom');
      context.element.find('.grid').off('row-click');

      if (context.grid) {
        context.grid.options.grid.destroy();
      }

      if (context.contextMenuColumn) {
        context.contextMenuColumn.destroy();
      }

      if (context.advancedFind) {
        context.advancedFind.destroy();
      }

      if (context.findWithinWidget) {
        context.findWithinWidget.destroy();
      }

      context._super();

    },

    _create: function () {
      const context = this;

      context._renderLayout();
      context._createAdvancedFindWidget();
      context._bindListeners();
      context._bindRowClickListeners();
      context._createContextualMenu();
      hitTermsHelper.setExistingTermsToFalse();

      searchResultsPreferenceHelper.getLayoutPrefAndLoadLastUsedSortFilter().done(function () {
        var winSearchResults = windowManager.getWindow().SESSION.searchResults;

        if (winSearchResults && winSearchResults.data) {
          searchResultsCreateHelper.setSearchResultsParametersToContext();
          searchResultsHelper.setNextStart(searchResultsHelper.getNextStart());
          winSearchResults.data.numFound = context._getPreferences('docFamilyFiltering') === 'noFiltering' ? context.totalResults : context.totalGroupedResults;

          window.setTimeout(function () {
            context.lastbuttonClicked = winSearchResults.lastbuttonClicked;
            if (searchResultsHelper.getPrevStart()) {
              searchResultsHelper.setPrevStart(searchResultsHelper.getPrevStart());
            }

            context.newSearch = false;
            searchResultsCreateHelper.setPagingParametersToContext(winSearchResults.sourceGadget, winSearchResults.lNumber);
          }, 200);
        } else {
          winSearchResults = {};
        }
      });

      if (window.CONFIG.mock) {
        context._loadData();
      }

      context._super();
    },
    _applyPreferences: function () {
      searchResultsPreferenceHelper.applyPreferences();
    },

    _setupGrid: function (context, pageNum, index, totalResults, skipRender) {
      var isUISortOrFilter = searchResultsHelper.isUISortOrFilter(context.sorts, context.filters);

      if (context._getPreferences('searchPagination') === 'manual') {
        context.grid.options.grid.setActiveCell(0, 0);
      }

      if (!skipRender) {
        context.grid.options.dataView.beginUpdate();
        context.grid.options.dataView.setItems(context.data.patents);
        context.grid.options.dataView.endUpdate();
      }

      //when there are no records to render when filters are applied - mainly tagged docs.
      if (gadgetManager.currentPage === 'estbrowser' && !$.isEmptyObject(context.filters) && context.data.patents.length === 0) {
        searchResultsBrowserHelper.resetToolBar();
      }

      var pageNumToSetActiveCell = pageNum; //maintain the pageNum before deallocating

      var isLastPageLoaded = searchResultsHelper.isLastPageLoaded(context.data.patents),
        filteredTerms = utilities.filteredItems(context.data.patents),
        pageCount = searchResultsHelper.fetchPageCount.call(context);

      if (context.grid && context._getPreferences('searchPagination') === 'manual' && (!isLastPageLoaded || isLastPageLoaded && filteredTerms.length === totalResults)) {
        var state = context.grid.options.paging.getGridNavState(),
          nextPageAvailable = state.pagingInfo.pageNum + 2 <= state.pagingInfo.totalPages;

        //Expand the family after deallocation -> Close/re-open SR
        pageNum = searchResultsManager._updatePageNum(pageNum, context.data.patents, context.totalResults, state, context.currentPageNumber);

        while (pageNum !== state.pagingInfo.pageNum) {
          nextPageAvailable = state.pagingInfo.pageNum + 2 <= state.pagingInfo.totalPages;

          if (nextPageAvailable) {
            context.grid.options.grid.setActiveCell(0, 0);

            // if next page is available, go to next page
            context.grid.options.paging.gridNavNext(pageCount);
            state = context.grid.options.paging.getGridNavState();
          } else {
            break;
          }
        }
        pageNum = pageNumToSetActiveCell; //use the pageNum before de-allocating to set active cell in the grid.

        if (isLastPageLoaded) {
          if (isUISortOrFilter) {
            if (context.lastDocId >= parseInt(pageCount)) {
              context.grid.options.grid.setActiveCell(context.lastDocId - pageNum * parseInt(pageCount), 0);
            } else {
              context.grid.options.grid.setActiveCell(context.lastDocId, 0);
            }
          } else {
            if (context.lastDocId === context.totalResults) {
              context.grid.options.grid.setActiveCell(context.data.patents.length - index - 1 - pageNum * parseInt(pageCount) - 1, 0);
            } else if (context.totalResults === context.data.patents.length) {//all patents loaded ex: TD or NV blue link click
              context.grid.options.grid.setActiveCell(context.lastDocId - pageNum * parseInt(searchResultsHelper.fetchPageCount.call(context)), 0);
            } else {
              context.grid.options.grid.setActiveCell(context.data.patents.length - index - 1 - pageNum * parseInt(pageCount), 0);
            }
          }
        } else {
          if (context.lastDocId >= parseInt(pageCount)) {
            context.grid.options.grid.setActiveCell(context.lastDocId - pageNum * parseInt(pageCount), 0);
          } else {
            context.grid.options.grid.setActiveCell(context.lastDocId, 0);
          }
        }

      } else if (isLastPageLoaded) {
        if (isUISortOrFilter) {
          if (context.lastDocId >= parseInt(pageCount)) {
            context.grid.options.grid.setActiveCell(filteredTerms.length - 1, 0);
          } else {
            context.grid.options.grid.setActiveCell(context.lastDocId - (totalResults - filteredTerms.length), 0);
          }
        } else {
          if (context._getPreferences('searchPagination') === 'manual') {
            context.grid.options.grid.setActiveCell(context.lastDocId - context.currentPageNumber * parseInt(pageCount), 0);
          } else {
            if (context.currentPatent || windowManager.getWindow().SESSION.sourceGadget === constants.TAGGED_DOCUMENTS) {//coming from blue link in TD, NV
              context.grid.options.grid.setActiveCell(context.lastDocId, 0);
            } else {
              context.grid.options.grid.setActiveCell(context.lastDocId - (totalResults - filteredTerms.length), 0);
            }
          }
        }
      } else {
        context.grid.options.grid.setActiveCell(context.lastDocId, 0);
      }

      context.setSelectedGridRows($(context.grid.options.grid.getActiveCellNode()).data('row') - 1);
      context._highlightClickedRow($(context.grid.options.grid.getActiveCellNode()).data('row') - 1, "activated");
    },

    _updateGreybarAndGrid: function (isUIOrSortFilter) {
      var context = this;
      var currentDocIndex = windowManager.getWindow().SESSION.searchResults.lastDocId,
        slickGridEle = context.element.find('.slick-viewport');
      if (currentDocIndex !== null && !$.isEmptyObject(context.grid)) {
        var rowClick = true,
          winSearchResults = windowManager.getWindow().SESSION.searchResults;
        context.grid.options.grid.invalidate();
        context.grid.options.grid.render();
        context.grid.options.grid.resizeCanvas();
        context.grid.options.grid.setSelectedRows([]);
        context.data.patents = winSearchResults.data.patents;
        context.lastbuttonClicked = winSearchResults.lastbuttonClicked;
        searchResultsHelper.setPrevStart(searchResultsHelper.getPrevStart(true));
        searchResultsHelper.setNextStart(searchResultsHelper.getNextStart(true));
        context.lastDocId = winSearchResults.lastDocId;
        context.currentPageNumber = Math.ceil((context.lastDocId + 1) / parseInt(searchResultsHelper.fetchPageCount.call(context))) - 1;

        if (isUIOrSortFilter && (context.grid.options.grid.getActiveCell() && context.grid.options.grid.getActiveCell().row !== currentDocIndex || !context.grid.options.grid.getActiveCell())) {
          context.grid.options.grid.invalidateAllRows();
          context.grid.options.dataView.beginUpdate();
          context.grid.options.dataView.setItems(context.data.patents);
          context.grid.options.dataView.endUpdate();

          if (context._getPreferences('searchPagination') === "manual") {
            context._refreshGridAfterActivate(isUIOrSortFilter);
            rowClick = false;
          }
        }
        searchResultsGreyBarHelper.updatePaging();
        searchResultsGreyBarHelper.updateDisplayResultsCount();

        if (rowClick) {
          context._highlightClickedRow(currentDocIndex, "activated");
          context.grid.options.grid.setActiveCell(currentDocIndex, 0);
          $(context.grid.options.grid.getActiveCellNode()).trigger('custom');
          if (currentDocIndex === utilities.filteredItems(winSearchResults.data.patents).length - 1) {
            setTimeout(function () {
              slickGridEle.scrollTop(slickGridEle[0].scrollHeight);
            }, 150);
          }
        }
      }
    },

    _receiveMessage: function (e) {
      var message = e.message,
        messageProcessor;

      messageProcessor = searchResultsMessageHandler[message.action];

      if (messageProcessor instanceof Function) {
        messageProcessor(e);
      }
    },

    _updateGrid: function (response, isGadgetAlreadyActive) {
      var context = this,
        queryId = 'none',
        win = windowManager.getWindow(),
        isUIOrSortFilter = searchResultsHelper.isUISortOrFilter(context.sorts, context.filters);

      if (win.SESSION.searchResults && win.SESSION.searchResults.searchQuery) {
        queryId = win.SESSION.searchResults.searchQuery.id;
      }

      if (response.script === context.options.script && !$.isEmptyObject(context.grid)) {
        // commented out because it happens for on demand as well
        if (!isGadgetAlreadyActive) {//no need to re-render If gadget is already active
          context._resize();
          context.grid.options.grid.invalidate();
          context.grid.options.grid.render();
          context.grid.options.grid.resizeCanvas();
        }
        var rowClick = true,
          winSearchResults = win.SESSION.searchResults;

        //handles inactive tab to active tab
        var currentDocIndex = winSearchResults.lastDocId,
          totalResults = context._getPreferences('docFamilyFiltering') === 'noFiltering' ? context.totalResults : context.totalGroupedResults;

        if (currentDocIndex !== null && currentDocIndex !== undefined) {
          context.data.patents = winSearchResults.data.patents;
          context.lastbuttonClicked = winSearchResults.lastbuttonClicked;

          context.lastDocId = winSearchResults.lastDocId;
          context.prevStart = winSearchResults.prevStart;
          context.nextStart = winSearchResults.nextStart;
          let tempPageNum = context.currentPageNumber;
          context.currentPageNumber = Math.ceil((context.lastDocId + 1) / parseInt(searchResultsHelper.fetchPageCount.call(context))) - 1;
          context.grid.options.grid.setSelectedRows([]);

          //Current Active Cell row and currentDocIndex can't be compared when crossing SR page boundary
          // as currentDocIndex always starts with 0 in Manual mode

          if (isUIOrSortFilter) {
            searchResultsHelper.setUniqueIds(winSearchResults.data.patents);
            context.data.patents = winSearchResults.data.patents;

            context.grid.options.dataView.beginUpdate();
            context.grid.options.dataView.setItems(context.data.patents);
            context.grid.options.dataView.endUpdate();

            searchResultsGreyBarHelper.updatePaging();
            searchResultsGreyBarHelper.updateDisplayResultsCount();

            if (context._getPreferences('searchPagination') === "manual") {
              context._refreshGridAfterActivate(isUIOrSortFilter);
              rowClick = false;
            }

            if (rowClick) {
              context.setSelectedGridRows(currentDocIndex);
              context._highlightClickedRow(currentDocIndex, "activated");
              context.grid.options.grid.setActiveCell(currentDocIndex, 0);
              //$(context.grid.options.grid.getActiveCellNode()).trigger('custom');
            }
          } else {
            context.grid.options.dataView.beginUpdate();
            context.grid.options.dataView.setItems(context.data.patents);
            context.grid.options.dataView.endUpdate();

            if (context._getPreferences('searchPagination') === constants.ON_DEMAND) {
              //temp fix to avoid viewport changed when set Active cell
              windowManager.getWindow().userPreferences.searchPagination = 'manual';

              if (searchResultsHelper.isLastPageLoaded(context.data.patents)) {
                context.grid.options.grid.setActiveCell(context.lastDocId - (totalResults - utilities.filteredItems(context.data.patents).length), 0);
                context.setSelectedGridRows($(context.grid.options.grid.getActiveCellNode()).data('row') - 1);
                context._highlightClickedRow(context.lastDocId - (totalResults - utilities.filteredItems(context.data.patents).length));
              } else {
                //let rowIndex = context.lastDocId - (context.prevStart + parseInt(searchResultsHelper.fetchPageCount.call(context)));
                context.grid.options.grid.setActiveCell(context.lastDocId, 0);
                context.setSelectedGridRows(context.lastDocId);
                context._highlightClickedRow(context.lastDocId, "activated");
                //context.grid.options.grid.setActiveCell(context.lastDocId, 0);
              }

              windowManager.getWindow().userPreferences.searchPagination = constants.ON_DEMAND;

              //$(context.grid.options.grid.getActiveCellNode()).closest('.slick-row').find('.result-num').trigger('click');

            } else if (context._getPreferences('searchPagination') === "manual") {
              var totalPages = Math.ceil(totalResults / searchResultsHelper.fetchPageCount.call(context));

              if (searchResultsHelper.isLastPageLoaded(context.data.patents)) {
                if (totalPages - context.currentPageNumber !== context.grid.options.paging.getGridNavState().pagingInfo.totalPages || tempPageNum !== context.currentPageNumber) {
                  context._refreshGridAfterActivate(isUIOrSortFilter);
                } else {
                  searchResultsGreyBarHelper.updateDisplayResultsCount();
                }
              } else {
                context._refreshGridAfterActivate(isUIOrSortFilter);
              }

              context.grid.options.grid.setActiveCell(context.lastDocId % searchResultsHelper.fetchPageCount.call(context), 0);
              context.setSelectedGridRows($(context.grid.options.grid.getActiveCellNode()).data('row') - 1);

              //$(context.grid.options.grid.getActiveCellNode()).closest('.slick-row').find('.result-num').trigger('click');
            }
          }
        }
      }
    },

    _clear: function () {
      var context = this;
      context.data.patents = [];
      context.data.numFound = 0;
      context.data.termHighlights = [];
      context.data.numberOfFamilies = 0;
      context.data.totalFilteredResults = 0;
      context.data.totalGroupedResults = 0;
      context.data.totalResults = context.data.patents.length;
      context.searchTerm = "";
      context.highlight = [];
      context.isCollectionSearch = false;
      context.isCollectionSearchData = {};
      context.totalFilteredResults = 0;
      context.totalGroupedResults = 0;
      context.totalResults = context.data.patents.length;
      context.resultCount = context.data.patents.length;
    },

    _renderLayout: function () {
      var strHtml = HBS['gadgets/searchResults/searchResults']({ main: true }),
        context = this;
      this.element.append(strHtml);

      this.findWithinWidget = new findWithinWidget({
        allowHitTermPlacement: true,
        title: context.title,
        gadgetName: 'searchResults',
        searchContainer: 'slick-viewport',
        clickCallback: context._resize.bind(context),
        searchCallback: function () {
          searchResultsFindHelper.handleFindWithinSearch(context, true, false);
        },
        searchChangedCallback: function () {
          var strSearch = context.element.find('.controls .filterInput').val();
          var currentUserInputs = context.advancedFind._getUserInputs();
          var isFindWithinSearch = context.advancedFind.element.is(':hidden');
          return context.findWithinWidget.hasSearchModified(strSearch, context.searchTerm, context.findWithinWidget.options.advOptions, currentUserInputs, isFindWithinSearch) ||
          context.advancedFind.element.is(':visible') && context.isCellRangeChanged;
        },
        hideCount: false,
        useOwnEllipsis: true
      }, this.element.find('.searchTool'));

      this.$panel = this.element.closest('.panel');
      this.$tabcontrols = this.$panel.find('.tabcontrols');
      this.$container = this.element.find('.container');
      this.$header = this.element.find('.header');
      this.$content = this.element.find('.contentgrid');
      this.$resultValueView = this.element.find('.resultInfo');
      this.$resultValueView.hide();
    },

    _loadData: function (westbrowser) {
      var context = this,
        deferred;

      if (westbrowser) {//flag for WEST side by side search US149026
        context.westbrowser = westbrowser;
      }
      context._renderConfig();
      deferred = context._getData(true);
      return deferred;
    },

    /**
     * errorNumFoundResponse
     * @description  Handle the error response from the count call.
     * @param {Object} response:API Response
     * @param String textStatus : String that contains the value error , if the counts call failed due to  valid error.
     */
    errorNumFoundResponse: function (response, textStatus) {
      const context = this;
      context._hideLoader();
      // if counts call fails search call needs to be aborted
      searchResultsManager.cancelAjaxCalls(context, textStatus, response.status);
      //US557543 Removed sorting condition blnSort for standardization
      windowManager.getWindow().SESSION.searchResults = {};
      context.data.patents = [];
      context.data.numFound = 0;
      context._hideLoader();
      windowManager.getWindow().SESSION.currentDocumentBeingViewed = {};
      windowManager.getWindow().SESSION.searchWithCountsStarted = false;
      context.element.find('.resultInfo').hide();

      const errorText = response.status === 429 && response.responseJSON && response.responseJSON.message !== 'Too many requests' || response.status === 422 ? response.responseJSON.message : constants.NON_SQM_ERROR_TEXT;

      context.element.find('.grid').html('<div class="errormessage">' + errorText + '</div>');

      searchResultsHelper.sqmSendNotification(errorText);

      messageManager.send({
        action: 'MESSAGE-no-search-results',
        options: { error: true }
      });

      searchResultsGreyBarHelper.updatePaging();
    },

    /**
     * numFoundSuccess
     * @description  This function is invoked on success of counts call when the response has no searchError.
     * @param {Object} response:API response
     */
    numFoundSuccess: function (response) {
      var context = this,
        totalResults = response.numResults;

      context.searchQuery.id = response.id;
      context.searchQuery.dateCreated = response.dateCreated;
      context.searchQuery.numResults = response.numResults;
      context.searchQuery.pNumber = response.pNumber;
      context.searchQuery.tags = [];

      windowManager.getWindow().extSearchParams = null;
      windowManager.getWindow().SESSION.search.queryId = response.id;
      response.databases = context.searchQuery.databases;
      windowManager.getWindow().SESSION.searchResults.searchQuery = response;

      if (totalResults > 0) {

        //if Search Option is Browse preserve the current query for browser window if Abort happens on Main Window Search Call
        if (context.searchOption === 'browse') {
          //Delete prevQuery from SESSION
          delete windowManager.getWindow().SESSION.prevQuery;
          searchResultsHelper.resetPrevQuery(response.id, context.searchOption, context.sorts, context.searchQuery, context.totalResults);
        }
      } else {
        context._hideLoader();
        messageManager.send({
          action: 'MESSAGE-no-search-results'
        });
        // US149345 : The below condition is to check the readyState of ajax call. This addresses a race condition when
        // search results count is zero and some times, the
        // searchWithBEFamily finishes before counts. When this happens counts call overwrites the data
        // set in session by searchWithBEFamily call. At this time when opening the DF gadget extended window
        // throws a console error and there is a continuous spinning gear in the window.
        if (context.summaryXHR && context.summaryXHR.readyState !== 4) {//counts before BEFamily
          console.log('BEFamily finished AFTER counts -->' + context.summaryXHR.readyState);
          windowManager.getWindow().SESSION.searchResults = {};
          windowManager.getWindow().SESSION.currentDocumentBeingViewed = {};
        } else {//counts after BEFamily
          console.error('BEFamily ajax call state is -->' + context.summaryXHR.readyState);
          console.error('BEFamily finished BEFORE counts');
        }


        context._clear();
        context.element.find('.page-number').hide();
        context.element.find('.visibleResults').hide();
        messageManager.send({
          action: 'MESSAGE-documentViewer-clear-text'
        });
        setTimeout(function () {
          liveRegion.text('No Search Results have returned for the query.');
        }, 0);
      }

      if (response.spellCheckResults) {
        windowManager.getWindow().SESSION.spellCheckResults = response.spellCheckResults;
      }
      // if condition was added because for small count the search results is returned faster and rendered ,the grid is deleted here , so to avoid this if condition is added

      //Update the searchQuery with parsed query used in highlights on/off
      context.searchQuery.parsedQuery = response.parsedQuery;

      context.element.find('.controls .resultInfo').css('display', 'inline-block');
      context.element.find('.controls .resultNumber').text(totalResults);

      //Refresh the SearchHistory gadget
      messageManager.send({
        action: 'MESSAGE-searchResults-data',
        options: {
          query: response
        }
      });
      if (context.searchOption === 'list') {
        //keep search button disabled
        messageManager.send({ action: 'MESSAGE-search-enable-search-buttons', data: 'search' });
      } else {
        messageManager.send({ action: 'MESSAGE-search-enable-search-buttons' });
      }
    },

    /**
     * numFoundFailed
     * @description  This function is invoked on success of counts call when the response has no searchError.
     * @param {Object} response:API response
     */
    numFoundFailed: function (response) {
      var context = this;
      context._hideLoader();
      context._clear();
      context.element.find('.resultInfo').hide();

      messageManager.send({
        action: 'MESSAGE-no-search-results',
        options: { error: true }
      });

      windowManager.getWindow().SESSION.searchResults = {};
      windowManager.getWindow().extSearchParams = null;
      messageManager.send({
        action: "MESSAGE-empty-documentViewer"
      });
      if (context._getPreferences('showResults') === constants.SHOWRESULTS_NO) {// for New Search and Error in NumFound Response
        searchResultsHelper.sendNotification(response.error.errorMessage);
      }

      context.element.find('.grid').html('<div class="errormessage"> Query Error : ' + response.error.errorMessage + '</div>');

    },

    /**
     * successNumFoundResponse
     * @description  This function is invoked on success of counts call.
     * @param {Object} response:API response
     */
    successNumFoundResponse: function (extSearchQueryType, response) {
      //handle external query search response
      response = extSearchQueryType ? response.queryResultList[0] : response;
      var numPrefix = 'L',
        context = this;
      if (response.pNumber) {
        windowManager.getWindow().SESSION.searchResults.lNumber = context.lNumber = ' ' + numPrefix + response.pNumber + ': ';
        windowManager.getWindow().SESSION.search.lNumber = context.lNumber;
        context.element.find('.controls .lQuery').text(context.lNumber);
      }

      delete windowManager.getWindow().SESSION.resultCount;
      //Retain this # for gray bar , can't keep it in SearchResults since searchResults can be emptied out
      windowManager.getWindow().SESSION.search.totalResults = windowManager.getWindow().SESSION.resultCount = context.resultCount = response.numResults;

      context.setLastButtonClicked(false);

      var searchError = response.error;

      context.totalResults = response.numResults;

      windowManager.getWindow().SESSION.spellCheckResults = null;

      if (searchError === null) {
        context.numFoundSuccess(response);
      } else {
        context.numFoundFailed(response);
      }
      searchResultsGreyBarHelper.updatePaging();
    },

    /** 
     * @description  This method is called when SR gadget is created/rerendered or new search is run
     * @param blnLoadData - is a flag to load new data from API
     * @param blnSort - is a flag when sort is changed
     * @memberof searchResults
     * @method _getData
     **/
    _getData: function (blnLoadData, blnSort) {
      var context = this,
        deferred = $.Deferred();

      if (!blnSort) {
        context.element.find('.grid').html('');
      }

      context._showLoader();

      if (blnLoadData) {
        context.newSearch = true;
        messageManager.send({
          action: 'MESSAGE-documentViewer-resetCurrentDoc'
        });

        if (context.searchQuery && context.searchQuery.q === '') {
          context._hideLoader();
          return deferred.promise();

        } else if (context.searchQuery && context.searchQuery.id) {
          return context.getSearchResults(blnLoadData, blnSort);
        } else {

          if (context.queryId !== null) {
            context.searchQuery.id = parseInt(context.queryId);
          }

          if (context.searchQuery.q === "t0" || context.searchQuery.ignorePersist === true) {
            return context._handleNonPersistentSearch(blnLoadData, blnSort);


          } else {
            //US570724 Whether to perform precheck or not
            const shouldPrecheck = context._shouldPrecheck();
            //US570724 added SQM precheck

            context._sqmPrecheck(shouldPrecheck).done(function () {
              messageManager.send({ action: 'MESSAGE-search-disable-search-buttons' });
              context._handlePreviousSearch();
              context.searchQuery.userId = window.userId;
              context.searchQuery.userDisplayName = window.displayName;

              searchResultsGridHelper.resetSRGrid();
              context._getQueryCounts(context.searchQuery, deferred);

              if (context.searchOption === 'search' || context.searchOption === 'browse' || context.searchOption === 'list' ||
              context.searchOption === 'listH' || context.searchOption === 'pn') {
                context.getSearchResults(blnLoadData, blnSort);

              } else {
                context._hideLoader();
                messageManager.send({
                  action: "MESSAGE-documentViewer-clear-text"
                });
              }

              if (context.searchQuery.hasOwnProperty('queryId')) {
                delete context.searchQuery.id;
              }

              context.queryId = null;
              context.element.find('.controls.info .resultInfo').hide();

              return deferred.promise().then(context.successNumFoundResponse.bind(context, context.searchQuery.extSearchQueryType), context.errorNumFoundResponse.bind(context));

            });
          }
        }
      } else {
        context._renderPreviouslyloadedData(blnLoadData);
      }
      context._resize();
    },

    /**
     * @description  This method is to check whether searchWithBEFamily endpoint will be called later.
     * Only perform the SQM precheck when both counts and searchWithBEFamily are invoked later.
     * @memberof _searchResults
     * @method _shouldPrecheck
     **/
    _shouldPrecheck: function () {
      const context = this;
      //conditions used for checking whether to call searchWithBEFamily endpoint
      return (
        context._getPreferences('showResults') === constants.SHOWRESULTS_YES ||
        context._getPreferences('showResults') === constants.SHOWRESULTS_LIMIT ||
        context.searchOption === constants.SEARCH_TYPE_BROWSE ||
        context.searchOption === constants.SEARCH_TYPE_LIST ||
        context.searchOption === constants.SEARCH_TYPE_SEARCH_HISTORY);

    },

    /**
     * @description  This is SQM precheck function that invokes a new endpoint '/termsExpansionCheck'
     * @param shouldPrecheck - is a boolean flag to decide whether to perform the precheck or not
     * @memberof searchResults
     * @method _sqmPrecheck
     **/
    _sqmPrecheck: function (shouldPrecheck) {
      const context = this,
        deferred = $.Deferred();
      //If shouldPrecheck === false, do not perform the precheck, resolve the promise.
      if (!shouldPrecheck) {
        deferred.resolve();
      } else {
        //If shouldPrecheck === true, use '/termsExpansionCheck' endpoint for precheck                     
        serviceManager.exec({
          url: services.getUrl('searchResults.termsExpansionCheck'),
          params: JSON.stringify(context.searchQuery),
          type: 'POST',
          contentType: 'application/json; charset=UTF-8',
          timeout: constants.API_TIMEOUT_5_MINS,
          notification: false,
          success: successResponse,
          error: errorResponse
        });

        //If it is successful with 200, resolve the promise
        function successResponse() {
          deferred.resolve();
        }
        function errorResponse(error) {
          const errorText = error.status === 422 ? error.responseJSON.error.errorMessage : constants.NON_SQM_ERROR_TEXT;
          context._hideLoader();
          //if error code is 422, precheck failed, no counts and BEFamily call will be invoked afterwards.
          if (error.status === 422) {

            context.element.find('.grid').html('<div class="errormessage">' + errorText + '</div>');
            searchResultsHelper.sqmSendNotification(errorText);
            deferred.reject();
          } else {
            //if error code is not 422, e.g. 500/401/404, precheck didn't work as expected, ignore precheck and proceed with counts and BEFamily calls.
            deferred.resolve();
          }
        }

      }
      return deferred.promise();
    },
    /**
     * @description  This gets called when when search results gadget is closed and opend
     * then previous search response should be loaded if there is any
     * @param blnLoadData - is a flag to load new data from API
     * @memberof searchResults
     * @method _renderPreviouslyloadedData
     **/
    _renderPreviouslyloadedData: function (blnLoadData) {
      var context = this;
      if (context.findWithinWidget) {
        context.findWithinWidget.reset();
        context.markedData = [];
      }
      if (context.element.find('.grid')) {
        if (context._getPreferences('docFamilyFiltering') !== 'noFiltering') {
          context.data.numFound = context.totalGroupedResults;
        }
        context.getDataResponse(blnLoadData, context.data);
      }
    },

    /**
     * @description  This method is to handle when browser search is inProgress
     * and subsequent search call is issued then previous (browser)search should be discarded
     * and browser window will issue API call for previous browser search
     * after it opened
     * @memberof searchResults
     * @method _handlePreviousSearch
     **/
    _handlePreviousSearch: function () {
      var context = this;
      if (context.summaryXHR && context.summaryXHR.readyState !== 4) {
        //First open the browser window for the currently existing search call
        if (context.prevSearchOption === 'browse') {
          context.prevSearchOption = '';
          searchResultsBrowserHelper.setParamsForBrowserWindow();
          if (windowManager.getWindow().SESSION.prevQuery) {
            var params = {
              viewer: 'estbrowser',
              extended: false,
              params: {
                queryId: windowManager.getWindow().SESSION.prevQuery.queryId,
                query: windowManager.getWindow().SESSION.prevQuery.query,
                searchOption: 'browse',
                sort: context.sorts,
                size: searchResultsHelper.getSearchPaginationSize()
              },
              queryId: windowManager.getWindow().SESSION.prevQuery.queryId
            };
            windowManager.openViewer(params, {});
          }
        }
        context.summaryXHR.abort();
      }
    },

    _applySortAndFilter: function (patents, size) {
      var winSESSION = windowManager.getWindow().SESSION,
        context = this;
      if (context.newSearch) {
        patents = searchResultsSortHelper._sortResultsUIAndSolr(context.sorts, false, true, patents);
      }
      if (context.searchQuery.q !== 't0' && !context.isCollectionSearch) {
        if (context._getPreferences('docFamilyFiltering') === 'noFiltering') {
          if (context.newSearch && (context.totalResults >= constants.CUSTOM_SORT_PAGE_SIZE ||
          patents.length < context.totalResults /*Filter applied*/)) {
            context.searchQuery.numResults = context.totalResults = winSESSION.searchResults.totalResults = patents.length;
          }
        } else {
          var totalFamilies = utilities.filteredItems(patents).length;
          if (context.newSearch && (windowManager.getWindow().SESSION.searchResults.data.totalGroupedResults > constants.CUSTOM_SORT_PAGE_SIZE ||
          totalFamilies < windowManager.getWindow().SESSION.searchResults.data.totalGroupedResults /*filter applied*/)) {
            context.totalGroupedResults = context.totalFilteredResults = totalFamilies;
          }
        }
      }
      var cachedPatents = [],
        response = {};

      response['patents'] = $.extend(true, [], patents);

      if (context.newSearch) {
        cachedPatents = searchResultsPrefetchHelper.cachePatents(response, cachedPatents, size); //Caching should be done for onDemand mode
        var prefetchNStart = searchResultsHelper.getNextStart() + constants.SEARCH_PREFETCH_PAGE_SIZE;

        if (context._getPreferences('docFamilyFiltering') === 'noFiltering' && prefetchNStart >= context.totalResults || context._getPreferences('docFamilyFiltering') !== 'noFiltering' && prefetchNStart >= context.totalGroupedResults) {
          prefetchNStart = -1;
        }

        if (context._getPreferences('searchPagination') === 'ondemand' && context._getPreferences('docFamilyFiltering') !== 'noFiltering' && constants.CUSTOM_SORT_PAGE_SIZE === size) {
          cachedPatents = []; //if page size is 10K ondemand mode and custom sort n filter is applied then no need to cache
        }

        searchResultsHelper.updateCachedPage(cachedPatents, searchResultsHelper.getPrevStart(), prefetchNStart, searchResultsHelper.getNextStart());
      }
      context.data['patents'] = response.patents;
      context.data['perPage'] = size;
      delete context.data.totalPages;
      context.data['numFound'] = context.data['totalResults'] = context.data['numResults'] = context.totalResults;
      context.data['numberOfFamilies'] = context.totalGroupedResults;
      searchResultsHelper._setUniqueIdAndRowNums(context.data.patents);

      windowManager.getWindow().SESSION.searchResults['data'] = context.data;
      windowManager.getWindow().SESSION.searchResults.data.groupedResults = context.totalGroupedResults;
      windowManager.getWindow().SESSION.searchResults.data.totalGroupedResults = context.totalGroupedResults;
      windowManager.getWindow().SESSION.searchResults.totalResults = context.totalResults;

      //No caching for Manual mode when Custom sort n filter is applied
      if (context._getPreferences('searchPagination') === 'manual' && windowManager.getWindow().SESSION.searchResults.cachedPage) {
        windowManager.getWindow().SESSION.searchResults.cachedPage.patents = [];
      }

    },

    /**
     * _getQueryCounts
     * @description  executes the counts call for the search query.
     * @param {Boolean} clearDfGadget: flag that is sent to clear Document Filter gadget
     * @param {Object} searchQuery: query object received from search gadget
     * @param {Object} deferred: deferred object that should be resolved to calling function so as to make the Success or error Calls
     */
    /*Care should be taken that the highlight terms displayed in the DocumentTextViewer should always be in the HitTerms displayed in the SR gadget.
     If that does not happen, we should display default color/ no color to the term but still should display in the DV.
     This will be a new requirement from the APOs in the future  */
    _getQueryCounts: function (searchQuery, deferred) {
      //reset the hitterms Session as we are executing a new query now
      hitTermsHelper.resetHittermsSession();
      //handle external query search
      if (searchQuery.extSearchQueryType) {
        serviceManager.exec({
          url: services.getUrl('search.externalCounts', {
            queryType: searchQuery.extSearchQueryType
          }),
          type: 'POST',
          params: JSON.stringify(searchQuery),
          success: deferred.resolve,
          error: deferred.reject,
          contentType: 'application/json'
        });
      } else {
        //regular counts call
        serviceManager.exec({
          url: services.getUrl('searchResults.numFound'),
          params: JSON.stringify(searchQuery),
          type: window.CONFIG.mock ? 'GET' : 'POST',
          contentType: 'application/json; charset=UTF-8',
          timeout: 300000,
          success: deferred.resolve,
          error: deferred.reject,
          notification: false
        });
      }

      //  Flag to identify search with counts initiated
      windowManager.getWindow().SESSION.searchWithCountsStarted = true;

      deferred.promise().then(function (data) {
        //handle external query search response
        if (searchQuery.extSearchQueryType) {
          data = data.queryResultList[0];
          messageManager.send({
            action: 'MESSAGE-search-externalQueryUpdate',
            options: data
          });
        }
        if (data.numResults > 0) {
          if (data.facets !== undefined && data.facets.length > 0) {
            var fcount = $.map(data.facets, function (facet) {
              return {
                id: facet.id,
                count: facet.count
              };
            });
          }
          windowManager.getWindow().SESSION.searchResults['facetCount'] = fcount;
          var basehitterms = hitTermsHelper.getHittermsFromCount(data);
          searchResultsHittermHelper.getHitTermCountHighlights(basehitterms);

        }
      });
    },



    _getConfig: function () {
      var context = this;
      context._renderConfig();
      context._getData(false);
    },

    scrollGridAfterNewData: function (position, responseSize) {
      const context = this;

      // scroll grid in such a way that last record of previous result is displayed in the last row
      if (context._getPreferences('searchPagination') === 'ondemand') {
        // refresh the grid so the result numbers refresh
        context.grid.options.grid.invalidate();
        context.grid.options.grid.render();

        if (position === 'next' && !context.lastbuttonClicked) {
          context.grid.options.grid.scrollRowIntoView(utilities.filteredItems(context.data.patents).length - responseSize - 1, true);
        } else {
          context.grid.options.grid.scrollRowToTop(responseSize);
        }
      }
    },

    calculateLastSelectedDocument: function (args) {
      const context = this;

      // if there is no search results data
      // don't do anything
      if (searchResultsHelper.getSearchResults().data && $.isEmptyObject(searchResultsHelper.getSearchResults().data.patents)) {
        return;
      }

      // update the last selected row to be primarily used for
      // tagging the last interacted document
      // by getting the difference of selected rows
      let selectedRanges = args.grid.getSelectionModel().getSelectedRanges();
      let oldRangesToCompare = context.oldRangesToCompare ? context.oldRangesToCompare : [];

      let newRows = args.grid.getSelectionModel().rangesToRows(selectedRanges);
      let oldRows = args.grid.getSelectionModel().rangesToRows(oldRangesToCompare);

      let docIndex;

      // if there are only 1 row selected
      // make that row as last item
      if (newRows.length === 1) {
        docIndex = searchResultsHelper.getRowToDocIndex(newRows[0], context);

        context.setLastSelectedDocument(searchResultsHelper.getDocumentObjectAtIndex(docIndex));
      } else if (newRows.length > 1) {
        // if there are more than 1 rows selected
        // we need to figure out which row was the last one selected

        let newSelectedRow = utilities.arrayDiff(newRows, oldRows || []);

        // we need to figure out the direction here in order to either set the first or last row as last item
        // if the difference row is less than the first row
        if (newSelectedRow[0] > newRows[0]) {
          docIndex = searchResultsHelper.getRowToDocIndex(newRows[newRows.length - 1], context);
        } else {
          docIndex = searchResultsHelper.getRowToDocIndex(newRows[0], context);
        }

        context.setLastSelectedDocument(searchResultsHelper.getDocumentObjectAtIndex(docIndex));
      }

      context.oldRangesToCompare = selectedRanges;
    },

    setLastSelectedDocument: function (lastDocumentSelected) {
      this.lastSelectedDocument = lastDocumentSelected;
      windowManager.getWindow().SESSION.searchResults.lastSelectedDocument = {
        guid: lastDocumentSelected.guid,
        type: lastDocumentSelected.type
      };
    },

    getLastSelectedDocument: function () {
      const context = this;

      let lastRow = null;

      if (context.lastSelectedDocument) {
        lastRow = searchResultsHelper.getIndexOfDocument(this.lastSelectedDocument);
      } else {
        let docViewerGadget = gadgetManager.getGadgetsByScript('documentViewer');

        // if DV exists
        // use the document from session to tag
        if (docViewerGadget.length > 0) {
          lastRow = searchResultsHelper.getIndexOfLastViewedDocument();
        }
      }

      return lastRow;
    },

    _toggleShowInfo: function () {
      var context = this;

      /** check if AF is open */
      var isAFshowing = context.advancedFind.element.is(':visible');
      /** check if Setting is open */
      var isSettingshowing = context.element.find('.meta-data-settings').is(':visible');

      var isTotalResultOverSize = context.totalResults > 99000;

      //if either
      /** if either AF or Settings is open show or hide accordingly */
      if (isAFshowing || isSettingshowing) {
        context.element.find('.highlightInfo').hide();
        context.element.find('.visibleResults').addClass('short-details');
        if (isTotalResultOverSize) {
          context.element.find('.resultNumberText').hide();
        } else {
          context.element.find('.resultNumberText').show();
        }
      } else {
        context.element.find('.visibleResults').removeClass('short-details');
        context.element.find('.highlightInfo').show();
        context.element.find('.visibleResults').show();
        context.element.find('.resultNumberText').show();
      }
      context._resize();
    },

    _bindListeners: function () {
      var context = this;

      context.element.find('.contentgrid').off('click', '.btn-new-tab').on('click', '.btn-new-tab', searchResultsEventHandler.onClickApplicationNumberLink.bind(context));
      context.element.find('.controls').off('click', '.advancedFind').on('click', '.advancedFind', searchResultsEventHandler.onClickAdvancedFind.bind(context));
      context.element.find('.contentgrid').off('keydown', '.grid').on('keydown', '.grid', searchResultsEventHandler.onKeyDownContentGrid.bind(context));
      context.element.find('.contentgrid').off('keyup', '.grid').on('keyup', '.grid', searchResultsEventHandler.onKeyUpContentGrid.bind(context));
      context.element.off('column-change', '.grid').on('column-change', '.grid', searchResultsEventHandler.sRGridColumnChange.bind(context));
      context.element.find('.controls').off('change', '.filterInput').on('change', '.filterInput', searchResultsEventHandler.findWithinChangeEventOnControls);
      context.element.find('.controls').off('keyup', '.filterInput').on('keyup', '.filterInput', searchResultsEventHandler.findWithinKeyupEventOnControls);
      context.element.find('.searchBox .icon').off('click').on('click', searchResultsEventHandler.clickOnFindWithinSearchIcon.bind(context));
      context.$header.off('click', '.searchSettings').on('click', '.searchSettings', searchResultsEventHandler.onClickHeaderSearchSettings);
      context.element.find('.meta-data-settings').off('click', '.close').on('click', '.close', searchResultsEventHandler.onClickSettingsClose.bind(context));
      context.element.find('.meta-data-settings').off('keyup', '.close').on('keyup', '.close', searchResultsEventHandler.onKeyUpMetadataSettings);
      context.element.off('click', '.knob.fontSize').on('click', '.knob.fontSize', searchResultsEventHandler.sRPreferencesEvent);
      context.element.find('.controls').
      off('click', '.highlightInfo .highlighter').
      on('click', '.highlightInfo .highlighter', searchResultsEventHandler.onClickHighlighter.bind(context));
      context.element.find('.meta-data-settings').
      off('change', '.setting-menu-options input').
      on('change', '.setting-menu-options input', searchResultsEventHandler.onChangeSettingsInput);
      context.element.find('.moreButton').off('click').on('click', searchResultsEventHandler.onClickMoreButton.bind(context));
      context.element.find('.resultInfo .page-number .btn-next').off('click').on('click', searchResultsEventHandler.onClickGridNavNext.bind(context));
      context.element.find('.resultInfo .page-number .btn-prev').off('click').on('click', searchResultsEventHandler.onClickGridNavPrev.bind(context));
      context.element.off('viewport-changed', '.grid').on('viewport-changed', '.grid', searchResultsEventHandler.onViewportChanged.bind(context));


      context.element.find('.knobs').off('click', '.knob.print').on('click', '.knob.print', searchResultsEventHandler.print.bind(context));
      context.element.find('.knobs').off('click', '.knob.export-csv').on('click', '.knob.export-csv', searchResultsEventHandler.csvExport.bind(context));
    },

    enableOrDisablePrintBtn: function (selectedRows) {
      var context = this;
      var blnDisbaled = selectedRows && selectedRows.length >= 1 ? false : true;

      context.element.find('#search-results-print-btn').prop('disabled', blnDisbaled);
    },

    /**
     * @description Function to get more search data
     * @param position str - direction the search is being performed (forward, backwards, etc)
     * @param blnIsFirst - TODO what is this?
     */
    _getMoreSearchData: function (position, blnIsFirst) {
      var context = this,
        intStartTime = new Date().getTime(),
        strMetricId = logManager.getUniqueId(),
        deferred;

      deferred = $.Deferred();

      // disable next click event until next results are in
      searchResultsGreyBarHelper.disableNavigationButtons();

      if (context.ajaxRequest && context.ajaxRequest.statusText !== undefined && context.ajaxRequest.statusText !== 'timeout') {
        if (context._getPreferences('searchPagination') === 'manual' && context.grid) {
          context.grid.options.paging.gridNavNext(searchResultsHelper.fetchPageCount.call(context));
        }
        searchResultsGreyBarHelper.enableNavigationButtons();
        deferred.reject();
        return deferred.promise();
      }

      context.element.find(".loadingButton").show();

      var performPrefetch = searchResultsPrefetchHelper.doPrefetch(context.sorts.ui, context.filters);
      // default size to load is 100
      var size = searchResultsHelper.getSearchPaginationSize();
      var pointer = searchResultsDataHelper._fetchData(performPrefetch, position, size);

      //prefetch is only needed when user clicks on last/first doc button and performPrefetch is true.
      var prefetchSize = performPrefetch ? size + constants.SEARCH_PREFETCH_PAGE_SIZE : size;

      windowManager.getWindow().SESSION.searchResults.requestComplete = false;

      //execute API call
      context.ajaxRequest = searchResultsManager.getMoreData(context.searchQuery, pointer, prefetchSize, context.sorts.solr.sortStr || context.sortStr).done(function (response) {
        response = typeof response === 'string' ? JSON.parse(response) : response;
        searchResultsDataHelper.gmdGetDataResponse(response, {
          'blnIsFirst': blnIsFirst,
          'strMetricId': strMetricId,
          'intStartTime': intStartTime,
          'position': position,
          'performPrefetch': performPrefetch,
          'pointer': pointer
        },
        deferred);
      }).fail(function () {
        searchResultsDataHelper.gmdErrorDataResponse(deferred);
      });

      return deferred.promise();
    },

    _handleSearchSubmit: function (searchButton, e) {

      if (searchButton === 'hitTerms') {
        var gadgets = gadgetManager.getGadgetsByScript('hitTerms');
        //Check if gadget is already open - If yes, focus
        if (gadgets && gadgets.length >= 1) {
          gadgetManager.showGadgetMenu($(this), 'hitTerms', gadgets[0], true);
        } else {
          //spawn the Hit Terms gadget in an extended window (if needed)
          switch (gadgetManager.currentPage) {
            case "estconsole":
              var width = 500,
                intMaxWidth = window.screen.availWidth,
                left = intMaxWidth - intMaxWidth / 3;
              gadgetManager.openGadgetInExtWindow('hitTerms', {
                hitTermsRunning: true
              }, true, {
                top: 80,
                left: left,
                height: 700,
                width: width
              });
              break;
            case "estbrowser":
              var data = {};
              gadgetManager.showGadgetMenu($('#search-results-more-highlights-btn'), 'hitTerms', data);
              e.stopPropagation();
              break;
            default:
              break;
          }
        }
      }
    },

    _bindGridListeners: function () {
      var context = this;

      if (context.storeUnsubscribe) context.storeUnsubscribe();

      context.storeUnsubscribe = tagManager.subscribe((action, tagNumbersAndPatentKeys) => {
        if (!context.grid) return null;

        const rowsToInvalidate = [];

        if (action === constants.SUBSCRIBTION_TAG_PATENT_REMOVED && context.fromtaggedlNumber) {
          return searchResultsNoteTagHelper._updateSRGrid.call(context, tagNumbersAndPatentKeys);
        }

        if (action === constants.SUBSCRIBTION_TAG_PATENT_ADDED || action === constants.SUBSCRIBTION_TAG_PATENT_REMOVED) {
          // find the affected patent within the sr data
          const gridItems = context.grid.options.dataView.getItems();

          const tagPatentKeysAffected = Object.values(tagNumbersAndPatentKeys).reduce((acc, current) => acc.concat(current), []);

          // invalidate rows that needs to be updated
          tagPatentKeysAffected.forEach((patentKey) => {
            const { guid, type } = utilities.getGuidAndTypeFromKey(patentKey);

            const rowIndex = utilities.filteredItems(gridItems).findIndex((patent) => patent.guid === guid && patent.type === type);

            rowsToInvalidate.push(rowIndex);
          });

          // if there are no rows to invalidate.. don't do anything else
          if (rowsToInvalidate.length > 0) {
            context.grid.options.grid.invalidateRows(rowsToInvalidate);
            context.grid.options.grid.render();
          }

          return null;
        }

        return null;
      });


      context.grid.options.grid.getSelectionModel().selector.onCellRangeSelected.subscribe(searchResultsGridEventHandler.onCellRangeSelection);
      context.element.find('.grid').off('keydown', '.slick-header .slick-header-column').on('keydown', '.slick-header .slick-header-column', searchResultsGridEventHandler.onKeyDownCopyColumnSelection.bind(this));
      context.element.find('.grid').off('resetconfig').on('resetconfig', searchResultsGridEventHandler.resetConfig.bind(context));
      context.element.find('.grid').off('click', '.slick-row .slick-cell .btn-add-print').on('click', '.slick-row .slick-cell .btn-add-print', searchResultsGridEventHandler.addPrintEvent.bind(this));
      context.element.find('.contentgrid').
      off('keyup', '.col-family-group .toggle').
      on('keyup', '.col-family-group .toggle', searchResultsGridEventHandler.familyGroupToggle.bind(this));
      context.grid.options.grid.onHeaderMouseEnter.subscribe(searchResultsGridEventHandler.onGridHeaderMouseEnter.bind(this));
      context.grid.options.grid.onClick.subscribe(searchResultsGridEventHandler.onClickGridEvent.bind(this));
      /**
       * onSelectedRowsChanged
       * @description    onSelectedRowsChanged slickgrid subscribe event
       * @param {object}  e
       * @param {object}  args
       */

      context.grid.options.grid.onSelectedRowsChanged.subscribe(searchResultsGridEventHandler.onSelectedRowsChanged.bind(this));

      context.grid.options.dataView.onPagingInfoChanged.subscribe(searchResultsGridEventHandler.onPagingInfoChanged.bind(this));

      context.grid.options.dataView.onRowCountChanged.subscribe(searchResultsGridEventHandler.onRowCountChanged.bind(this));

      context.grid.options.grid.onKeyDown.subscribe(searchResultsGridEventHandler.onKeyDown.bind(this));

      $(document).off('contextualMenu-item-clicked.' + context.contextMenuColumn.eventNamespace).on('contextualMenu-item-clicked.' + context.contextMenuColumn.eventNamespace, searchResultsEventHandler._handleContextMenuClickEvent.bind(context));

      context.element.find('.contentgrid').off('contextmenu', '.grid-canvas').on('contextmenu', '.grid-canvas', searchResultsEventHandler._updateContextMenuOptions.bind(this));
    },

    getRowsBasedOnRanges: function (ranges) {
      let rows = [];

      for (var x = 0; x < ranges.length; x++) {
        let difference = ranges[x].toRow - ranges[x].fromRow;

        // if difference is 0
        // it means its a single row
        if (difference === 0) {
          // push any to rows because both are the same row
          rows.push(ranges[x].fromRow);
        } else {
          // otherwise
          // push all rows starting from fromRow to toRow
          let allRows = Array(ranges[x].toRow - ranges[x].fromRow + 1).fill().map((_, index) => ranges[x].fromRow + index);
          rows = rows.concat(allRows);
        }
      }

      return rows;
    },

    _getSelectedRows: function () {
      var context = this;
      var rowIds = [];
      $.each(searchResultsHelper.getSelectedGridRows(context.getSelectedGridRows(), context.getSelectedDocumentRows()), function (i, rowId) {
        rowIds.push(rowId);
      });
      $.each(context.grid.options.grid.getSelectionModel().getSelectedRanges(), function (i, range) {
        if (range.isSingleRow()) {
          rowIds.push(range.fromRow);
        } else {
          for (i = range.fromRow; i <= range.toRow; i++) {
            rowIds.push(i);
          }
        }
      });
      return rowIds;
    },

    _createAdvancedFindWidget: function () {
      var context = this;
      var options = {
        gadgetName: context.options.title,
        gadgetScript: context.options.script,
        onClose: searchResultsFindHelper.collapseAdvancedFind.bind(context)
      };

      if (!context.advancedFind) {
        context.advancedFind = new AdvancedFindWidget(options, context.element.find(".advanced-find-options"));
      }
    },

    _toggleAdvancedFind: function (blnSkipHide, isOpenOrClosed) {
      var context = this;
      var element = context.element.find('.advancedFind');
      if (isOpenOrClosed === 0) {
        if (!blnSkipHide) {
          context.advancedFind._saveVisibleState(false);
          context.advancedFind.element.hide();
          $(element).attr({ 'aria-expanded': 'false', 'title': 'Open Advanced Find' }).focus();
          liveRegion.text('Search results advanced search options section has collapsed');
          context._toggleShowInfo();
        }
      } else {
        context.advancedFind._saveVisibleState(true);
        context.advancedFind.element.show();
        $(element).attr({ 'aria-expanded': 'true', 'title': 'Close Advanced Find' });
        liveRegion.text('Search results advanced search options section has expanded');
        context._toggleShowInfo();
        context.element.find('.findWithin-group input[type="text"]').focus();
      }
      context._resize();
    },

    _bindRowClickListeners: function () {
      var context = this;

      context.element.find('.grid').off('custom').on('custom', searchResultsEventHandler.onCustomGrid.bind(context));
      context.element.find('.grid').off('row-click').on('row-click', searchResultsEventHandler.onRowClickGrid.bind(context));
    },

    _getRowFromEvent: function (e) {
      var context = this;
      if (e && context.grid.options.grid.getCellFromEvent(e)) {
        return context.grid.options.grid.getCellFromEvent(e).row;
      }
    },

    _setCellSelection: function (context, ranges) {
      context.grid.options.grid.getSelectionModel().setSelectedRanges(ranges);
    },

    /**
     * @Function removeProgramSelectedRows
     * @description Removes the rows from getSelectedDocumentRows() and unselects the checkbox
     * @returns void
     */
    removeProgramSelectedRows: function () {
      var context = this,
        parentRow;
      if (context.selectedGridRows) {
        var rowsToRemove = context.selectedGridRows.filter(function (obj) {
          if (!obj.persist) {
            return obj.rowId;
          }
        });

        rowsToRemove.forEach(function (obj) {
          //get row index
          var index = context.selectedGridRows.indexOf(obj);

          if (index !== -1) {
            // remove single row from array
            let selectedRows = context.getSelectedGridRows();


            selectedRows.splice(index, 1);

            context.setSelectedGridRows(selectedRows);

            index = -1;
            // removes the checkbox selection
            parentRow = context.element.find('.rowid--id_' + obj.rowId);
            $(parentRow.find('.row-select-check')[0]).prop('checked', '');
          }

          index = context.getSelectedDocumentRows().indexOf(obj.rowId);
          if (index !== -1) {
            let selectedDocumentRows = context.getSelectedDocumentRows();

            selectedDocumentRows.splice(index, 1);

            context.setSelectedDocumentRows(selectedDocumentRows);
            index = -1;
          }
        });
      }

    },

    removeHighlights: function () {
      var context = this,
        rowsToRemove = context.getSelectedDocumentRows().filter(function (obj) {
          return !obj.persist;
        });

      rowsToRemove.forEach(function (obj) {
        //get row index
        var index = searchResultsHelper.getSelectedGridRows(context.getSelectedGridRows(), context.getSelectedDocumentRows()).indexOf(obj.rowId),
          parentRow;
        if (index !== -1) {

          // removes the checkbox selection
          parentRow = context.element.find('.rowid--id_' + obj.rowId);
          $(parentRow).removeClass('selected');
          if (parentRow[0] && parentRow[0].childNodes) {
            parentRow[0].childNodes.forEach(function (obj) {
              if ($(obj).hasClass('selected')) {
                $(obj).removeClass('selected');
              }
            });
          }
        }
      });
    },

    _clearYellowHighlights: function (context) {
      context.grid.options.dataView.getFilteredItems().forEach(function (element) {
        context.grid.options.grid.removeCellCssStyles("highlight");
        context.highlightClickedRowHash[element.rowNumber] = {};
      });
    },

    _highlightClickedRow: function (rowIndex) {
      var context = this;
      context.highlightClickedRowHash = {};
      context._highlight(rowIndex);
    },

    _highlight: function (rowIndex) {
      var context = this;
      context.grid.options.grid.removeCellCssStyles("highlight");
      context.highlightClickedRowHash[rowIndex] = {};

      $.each(context.grid.options.config, function () {
        context.highlightClickedRowHash[rowIndex][this.key] = 'activated';
      });

      context.highlightClickedRowHash[rowIndex]["_checkbox_selector"] = 'activated';
      context.grid.options.grid.addCellCssStyles("highlight", context.highlightClickedRowHash);

      if (context._getPreferences('searchPagination') === 'manual') {
        var state = context.grid.options.paging.getGridNavState();
        //TODO: This below assignment needs to be verified to better understand its use and add appropriate comments
        context.highlightClickedRowPage = state.pagingInfo.pageNum;
      }
    },

    _sendDocToDocViewer: function (msg) {
      windowManager.getWindow().SESSION.searchResults = windowManager.getWindow().SESSION.searchResults || {};
      windowManager.getWindow().SESSION.searchResults['docViewerDocumentId'] = msg.patent.guid;
      windowManager.getWindow().SESSION.searchResults['docViewerDocumentSource'] = msg.patent.type;
      windowManager.getWindow().SESSION.searchResults['docViewerLinks'] = msg.patent.links;
      windowManager.getWindow().SESSION.searchResults['patentIndex'] = msg.patentIndex;
      var docIndex = msg.patent.rowNumber = searchResultsHelper.findDocumentAtIndex(msg.patent.guid, msg.patent.type, msg.patentIndex);
      windowManager.getWindow().SESSION.currentDocumentBeingViewed = {
        documentId: msg.patent.guid,
        type: msg.patent.type,
        queryId: msg.patent.queryId ? msg.patent.queryId : msg.queryId,
        docSize: msg.patent.documentSize,
        docIndex: docIndex,
        gadgetId: -1, // we want the DV to receive this message and not discard as we are using gadget id equality check for retrieving and displaying images
        uniqueId: msg.patent.uniqueId,
        imageLocation: msg.patent.imageLocation
      };
      msg.navigateDirection = this.navigateDirection;
      msg.activeSearch = this.newSearch;
      msg.messageSourceGadget = "searchResults"; // to reset the lastSection to false in IMGV.
      msg.focussedGadgetId = documentViewerHelper.getFocusedDVId();
      if (this.sortingStarted === true) {
        msg.activeSearch = false;
      }

      this._sendMessage('MESSAGE-update-document-viewer', msg);
    },

    //TODO: Move to a a new settings helper file when there are more settings related helper functions
    _renderMetaData: function () {
      var context = this,
        strHtml,tagHtml;

      strHtml = HBS['gadgets/searchResults/searchResults']({ metadata: true, config: context.gridConfig });
      context.element.find('.meta-data-settings .columns-list').empty().html(strHtml);
      tagHtml = HBS['gadgets/searchResults/searchResults']({ tagdata: true, config: context.gridConfig });
      context.element.find('.meta-data-settings .tags-list ul').empty().html(tagHtml);
    },

    setLastButtonClicked: function (booleanToggle) {
      let context = this;
      let winSESSION = windowManager.getWindow().SESSION;

      context.lastbuttonClicked = booleanToggle;

      if (winSESSION.searchResults) {
        winSESSION.searchResults.lastbuttonClicked = booleanToggle;
      }
    },

    _renderConfig: function () {
      var context = this,
        columns = context.gridConfig,
        famColIndex = columns.map(function (x) {
          return x.key;
        }).indexOf('familyGroup'),
        familyIDFilteringON = context._getPreferences('docFamilyFiltering') !== 'noFiltering';

      // Only add it if its not in the config, after clearing preferences
      // and family id filtering is enabled
      if (famColIndex === -1 && familyIDFilteringON) {
        // Add fam ID column
        var famIdCol = {
          "key": "familyGroup",
          "label": "+",
          "size": 50,
          "unhideable": true,
          "visible": true,
          "sortable": false,
          "order": 1,
          "cssClass": "col-family-group notSortable"
        };

        // Insert column after "Tag 1"
        columns.splice(0, 0, famIdCol);
        //columns.splice(1, 0, famIdCol);
        //searchResultsGridHelper._updateGridColumnOrderConfig(columns);
      } else if (!familyIDFilteringON && famColIndex > -1) {
        // remove the column since its
        // family id filtering is off
        columns.splice(famColIndex, 1);
        //searchResultsGridHelper._updateGridColumnOrderConfig(columns);
      }

      $.each(columns, function (i, column) {
        switch (column.key) {
          case 'select':
            /*Builds the 'viewed' checkboxes on the results 'table'*/
            column.formatter = searchResultsGridFormatter.selectFormatter.bind(this);
            break;

          case 'rowNumber':
            column.formatter = searchResultsGridFormatter.rowNumberFormatter.bind(this);
            break;

          case 'familyGroup':
            column.formatter = searchResultsGridFormatter.familyGroupFormatter.bind(this);
            break;

          case 'documentId':
            column.formatter = searchResultsGridFormatter.documentIdFormatter.bind(this);
            break;

          case 'inventionTitle':
            column.formatter = searchResultsGridFormatter.inventionTitleFormatter.bind(this);
            break;

          case 'one':
          case 'two':
          case 'three':
          case 'four':
          case 'five':
          case 'six':
          case 'seven':
          case 'eight':
          case 'nine':
          case 'ten':
          case 'eleven':
          case 'twelve':
          case 'thirteen':
          case 'fourteen':
          case 'fifteen':
          case 'sixteen':
          case 'seventeen':
          case 'eighteen':
          case 'nineteen':
          case 'twenty':
          case 'twentyone':
          case 'twentytwo':
          case 'twentythree':
          case 'twentyfour':
          case 'twentyfive':
          case 'twentysix':
            column.formatter = searchResultsGridFormatter.tagGroupFormatter.bind(this);
            break;
          case 'unused':
            /*Builds the 'viewed' checkboxes on the results 'table'*/
            column.formatter = searchResultsGridFormatter.unusedFormatter.bind(this);
            break;
          case 'cited':
            /*Builds the 'viewed' checkboxes on the results 'table'*/
            column.formatter = searchResultsGridFormatter.citedFormatter.bind(this);
            break;
          case 'datePublished':
            column.formatter = searchResultsGridFormatter.datePublishedFormatter.bind(this);
            break;
          case 'applicationFilingDate':
            column.formatter = searchResultsGridFormatter.applicationFilingDateFormatter.bind(this);
            break;
          case 'applicationNumber':
            /*construct the hyperlink to DAV*/
            column.formatter = searchResultsGridFormatter.applicationNumberFormatter.bind(this);
            break;
          case 'imageDocDisplayed':
            break;
          case 'relatedApplFilingDate':
            //Domestic Priority
            column.formatter = searchResultsGridFormatter.relatedApplFilingDateFormatter.bind(this);
            break;
          case 'priorityClaimsDate':
            //Foreign Priority
            column.formatter = searchResultsGridFormatter.priorityClaimsDateFormatter.bind(this);
            break;
          case 'source':
            break;
          case 'applicantName':
            /*Update applicant Name to Blank for Derwent'*/
            column.formatter = searchResultsGridFormatter.applicantNameFormatter.bind(this);
            break;
          case 'assigneeName':
            /*Update assignee Name to Blank for Derwent'*/
            column.formatter = searchResultsGridFormatter.assigneeNameFormatter.bind(this);
            break;
          case 'notes':
            /*Builds the 'viewed' checkboxes on the results 'table'*/
            column.formatter = searchResultsGridFormatter.notesFormatter.bind(this);
            break;
          case 'notesTag':
            /*Builds the 'viewed' checkboxes on the results 'table'*/
            column.formatter = searchResultsGridFormatter.notesTagFormatter.bind(this);
            break;
          case 'score':
            /*Builds the 'viewed' checkboxes on the results 'table'*/
            column.formatter = searchResultsGridFormatter.scoreFormatter.bind(this);
            break;
          default:
            break;
        }
      });
      context._toggleShowInfo();
    },

    refreshGridFormatters: function () {
      // if grid doesn't exist.. do nothing
      if (!this.grid) {
        return;
      }

      // capture focused element
      let focusedElementID = document.activeElement.getAttribute('id');

      // in order for the select checkbox to be updated
      // we need to run the formatters again to recalculate the checkboxes
      this.grid.options.grid.invalidateAllRows();

      // Call render to render them again
      this.grid.options.grid.render();

      // we have to put focus back to grid, for improving performance it is
      // better to check if the element is visible, if not visible scroll it to view
      var focusedElement = document.getElementById(focusedElementID);
      if (focusedElement && focusedElement.offsetParent === null) {
        focusedElement.focus();
      } else {
        this.element.find('#' + focusedElementID).focus();
      }
    },

    // this is for marking the rows selected without
    // selecting the whole row with slick grid
    setSelectedDocumentRows: function (rows) {
      // if rows is a number
      // make it an array
      if (typeof rows === 'number') {
        rows = [rows];
      }

      this.selectedDocumentRows = rows;
    },

    // this is for getting the documents that has the select
    // column checked
    getSelectedDocumentRows: function () {
      return this.selectedDocumentRows ? this.selectedDocumentRows : [];
    },

    setSelectedGridRows: function (rows) {
      // if rows is a number
      // make it an array
      if (typeof rows === 'number') {
        rows = [rows];
      }

      // select the rows in grid
      // only select if it has not already been selected
      let selectedRows = this.grid.options.grid.getSelectedRows();

      // if the selected rows and new rows are not the same
      // set the new row as selected
      if (rows.length !== selectedRows.length || !rows.every(function (value, index) {
        return value === selectedRows[index];
      })) {
        this.grid.options.grid.setSelectedRows(rows);

        // refresh grid formatter
        this.refreshGridFormatters();
      }
    },

    getSelectedGridRows: function () {
      return this.grid ? this.grid.options.grid.getSelectedRows() : [];
    },

    parseCacheAndPrefetchPage: function (direction) {
      var context = this,
        patents,result,
        isUISortOrFilter = searchResultsHelper.isUISortOrFilter(context.sorts, context.filters);

      // reset last button clicked
      if (direction === 'previous') {
        context.setLastButtonClicked(false);
      }

      // disable navigation buttons
      searchResultsGreyBarHelper.disableNavigationButtons();

      result = searchResultsPrefetchHelper.getPatentsFromCacheForDisplay(context.pageSize, direction, context.lastbuttonClicked);

      patents = searchResultsManager.massageSearchResultsData(context.searchQuery.id, result.patents, direction, context.lastbuttonClicked, searchResultsHelper.getPrevStart(), searchResultsHelper.getNextStart(), isUISortOrFilter);
      //add CSS Rules for the terms that were just parsed from the latest data set
      searchResultsHittermHelper.setCssRuleForHitTerm();

      //Update Note Details
      if (!isUISortOrFilter) {//already populated if custom sort n filter is applied
        patents = notesManager._parseMapNoteDetails(patents);
      }

      // Limit Search result data
      context.data.patents = searchResultsHelper.limitSRDataMemory(direction, context.data.patents, patents, context.currentPageNumber);

      //This is needed because for UI sort n Fiter no more data fetching from API so ID's will not be updated
      if (isUISortOrFilter) {
        searchResultsHelper._setUniqueIdAndRowNums(context.data.patents);
      }

      var totalResults = context._getPreferences('docFamilyFiltering') !== 'noFiltering' ? windowManager.getWindow().SESSION.searchResults.data.totalGroupedResults :
      windowManager.getWindow().SESSION.searchResults.totalResults;

      if (totalResults === utilities.filteredItems(context.data.patents).length) {
        result.blnPrefetch = false; //All results are fetched
      }

      if (result.blnPrefetch) {
        context.prefetchRequest = true;
        searchResultsManager.prefetchSearchPage(context.sorts.solr.sortStr || context.sortStr, context.searchQuery, context.lastbuttonClicked, context.totalGroupedResults, context.totalResults, direction).done(function () {
          context.prefetchRequest = false;
          searchResultsGreyBarHelper.enableNavigationButtons();

          context.element.find(".loadingButton").hide();
        });
      } else {
        searchResultsGreyBarHelper.enableNavigationButtons();
      }
    },

    /**
     * Gets the image page count.
     * @private
     * @params value
     * @returns pagecount
     * @memberof searchResults
     */
    _getImagePageNumber: function (id, type) {
      if (windowManager.getWindow().SESSION.currentDocumentBeingViewed && windowManager.getWindow().SESSION.currentDocumentBeingViewed.documentId === id && windowManager.getWindow().SESSION.currentDocumentBeingViewed.type === type && windowManager.getWindow().SESSION.currentDocumentBeingViewed.pageNumber) {
        return windowManager.getWindow().SESSION.currentDocumentBeingViewed.pageNumber;
      } else {
        return 1;
      }
    },

    /**
     * Update Grid after activate Search Results in Manual Mode.
     * @private
     * @params context
     */
    _refreshGridAfterActivate: function (isUIOrSortFilter) {
      var context = this,
        totalResults = context._getPreferences('docFamilyFiltering') === 'noFiltering' ? context.totalResults : context.totalGroupedResults,
        index = 0,
        page = 0,
        winSESSION = windowManager.getWindow().SESSION,
        pageNum = context.currentPageNumber;

      //Doc Nav to Last, Close SR and open
      if (searchResultsHelper.isLastPageLoaded(context.data.patents)) {
        // this is fine when only the last page has been loaded...
        // but if previous page is also loaded... it should return 1 instead of 0
        // pageNum = allPages - pageNum;

        // divide the patents up by page size
        // pageNum = 3428 -> 0 // if only 1 page has been loaded
        // pageNum = 3428 -> 1 // if only 2 page has been loaded
        // last page results.. 8
        // previous page results is 10

        // 18 / 10 = round up 2 - 1 = 1
        // 8 / 10 = round up 1 - 1 = 0
        // pageNum = Math.ceil(utilities.filteredItems(context.data.patents).length / parseInt(searchResultsHelper.fetchPageCount.call(context))) - 1;


        let docIndex = utilities.filteredItems(context.data.patents).map(function (item) {
          return item.guid + item.type;
        }).indexOf(winSESSION.currentDocumentBeingViewed.documentId + winSESSION.currentDocumentBeingViewed.type) + 1;
        page = pageNum = Math.ceil(docIndex / parseInt(searchResultsHelper.fetchPageCount.call(context))) - 1;
      }

      if (isUIOrSortFilter) {
        var state = context.grid.options.paging.getGridNavState(),
          pageNumber = state.pagingInfo.pageNum;

        if ((context.currentPageNumber > 0 && context.currentPageNumber + 2 > state.pagingInfo.totalPages || pageNumber > 0 && pageNumber + 2 > state.pagingInfo.totalPages) && context.lastbuttonClicked) {
          page = state.pagingInfo.totalPages - 1;
        } else {
          page = context.currentPageNumber;
        }
      }
      if (context._getPreferences('searchPagination') === 'manual') {
        context.grid.options.dataView.setPagingOptions({
          pageNum: page
        });
      }

      context._setupGrid(context, pageNum, index, totalResults, true);
    },

    updateGridData: function (position) {
      var context = this;

      var size = searchResultsHelper.getSearchPaginationSize();

      try {

        let pointer = searchResultsManager.getPointerBasedOnNavigation(position, searchResultsHelper.getPrevStart(), searchResultsHelper.getNextStart());

        // figure out the difference between data and what is on grid
        let responsePatents = context.data.patents.slice(context.grid.options.dataView.getItems().length);

        let prevNextStartModel = {
          prevStart: searchResultsHelper.getPrevStart(),
          nextStart: searchResultsHelper.getNextStart()
        };

        // get prev/next start
        prevNextStartModel = searchResultsHelper.getPrevNextStart(prevNextStartModel, position, pointer, context.data.patents, responsePatents, context.lastbuttonClicked);

        searchResultsHelper.setPrevStart(prevNextStartModel.prevStart);
        searchResultsHelper.setNextStart(prevNextStartModel.nextStart);

        if (position === "next" && context.lastDocId > context.data.patents.length) {
          context.lastDocId = context.data.patents.length - 1;
          context.grid.options.grid.setActiveCell(context.lastDocId, 0);
        } else if (context.grid.options.grid.getActiveCell()) {
          context.grid.options.grid.setActiveCell(context.grid.options.grid.getActiveCell().row, 0);
        } else {
          context.grid.options.grid.setActiveCell(0, 0);
        }

        if (context._getPreferences('searchPagination') === 'manual') {
          if (position === "previous") {
            context.currentPageNumber = context.currentPageNumber - 1;
          }
        }

        context.grid.options.dataView.beginUpdate();
        context.grid.options.dataView.setItems(context.data.patents);
        context.grid.options.dataView.endUpdate();

        if (context._getPreferences('searchPagination') === 'manual') {
          context.grid.options.dataView.setPagingOptions({ pageSize: parseInt(searchResultsHelper.fetchPageCount.call(context)) });
        }

        // scroll the grid manually since the some results have been discarded
        context.scrollGridAfterNewData(position, size);

        // Update displaying results count
        searchResultsGreyBarHelper.updateDisplayResultsCount();

        if (context._getPreferences('searchPagination') === 'manual' && searchResultsHelper.getResultOffset() === 0) {
          context.grid.options.grid.setActiveCell(0, 0);
          if (position === 'next') {
            context.grid.options.paging.gridNavNext(searchResultsHelper.fetchPageCount.call(context));
          }
          windowManager.getWindow().SESSION.searchResults['pageNum'] = context.grid.options.paging.getGridNavState().pagingInfo.pageNum;
        }

        searchResultsFindHelper.applyFindWithin();
      } catch (err) {
        console.info(err);
      } finally {
        context.element.find(".loadingButton").hide();
      }
    },

    /**
     * It handles instantiating slickgrid instance and applying filter based on familyCount
     * @private
     * @param {Object} - SR gridConfig
     * @param {Object} - SR Data
     * @param {Boolean} - familyIDFiltering Settings
     * @param {Boolean} - virtualscrolling settings
     * @memberof searchResults
     */
    _handleCreateGrid: function (config, data, familyIDFilteringON, disableVirtualScrolling) {
      var context = this;
      context.grid = new Grid({
        config: config,
        data: data,
        multiColumnSort: true,
        sortStyle: "",
        columnPicker: true,
        resetColumns: true,
        clientSort: false,
        enableCellNavigation: true,
        enableDblClick: true,
        enableColumnSelection: true,
        selectActiveRow: false,
        enablePaging: true,
        disableVirtualScrolling: disableVirtualScrolling,
        useCheckBoxSelector: false,
        useCustomSelectionModel: true,
        useCopyCellManager: true,
        copyCellOptions: searchResultsCopyDataExtractor.pluginOptions
      }, context.element.find('.grid'));

      // Set filter to hide collapsed groups if filtering is on
      if (familyIDFilteringON) {
        context.grid.options.dataView.beginUpdate();
        context.grid.options.dataView.setFilter(searchResultsGridHelper.filterByFamily);
        context.grid.options.dataView.endUpdate();
      }
    },

    /**
     * Renders the grid with the latest session data and reset the total count and family count in the gray bar
     * @private
     * @memberof searchResults
     */
    renderGrid: function () {
      var context = this,
        familyIDFilteringON = context._getPreferences('docFamilyFiltering') !== 'noFiltering',
        data = context.data.patents,
        config = context.gridConfig,
        disableVirtualScrolling = context._getPreferences('enableAccessibility');

      if (context.grid) {
        context.grid.options.grid.destroy();
      }

      context._handleCreateGrid(config, data, familyIDFilteringON, disableVirtualScrolling);

      searchResultsGreyBarHelper.updatePaging();
      searchResultsGreyBarHelper.updateDisplayResultsCount();

      context.element.find('.toggleSections').css('display', 'none');
      context.element.find('.snippetSettings').css('display', 'none');
    },

    /**
     * Triggers resultNum cell or first cell on first row cell click event to highlight the row
     * @private
     * @memberof searchResults
     */
    _triggerGridClickEvent: function () {
      var context = this;
      if (context.currentPatent) {//If TD/NV loaded in SearchResults
        searchResultsNoteTagHelper.displaySearchResultsFromTaggedDocsOrNotesViewer();
      } else {
        // typeof context.lastDocId === 'number'
        // reverted the change because when SR is hidden.. the above logic doesn't work
        if (context.lastDocId) {
          var lastDocId = context.lastDocId;
          context.grid.options.grid.setSelectedRows([]);
          if (context._getPreferences('searchPagination') === 'ondemand' && context.lastDocId > constants.SEARCH_RESULT_MEMORY_LIMIT) {
            lastDocId = context.lastDocId - (parseInt(context.element.find('.notifyStart').text()) - 1);
          }
          context.grid.options.grid.setActiveCell(lastDocId, 0);
          $(context.grid.options.grid.getActiveCellNode()).closest('.slick-row').find('.result-num').trigger('click');
        } else {
          if (context.element.find('.grid .slick-row.rowid--id_0 .result-num').length && context.searchOption === 'listH') {
            context.element.find('.grid .slick-row.rowid--id_0 .result-num').trigger('click');
          } else {
            context.element.find('.grid .slick-cell:first').trigger('custom');
            searchResultsHelper._activateGridCell(0, 0, context.grid.options.grid); //DE46012 : needed for main/Browser window to put focus on first row.
          }

          context.grid.options.grid.scrollRowIntoView(0);
        }
      }
    },

    /**
     * It handles TD or Collection Searches where persistence of a query is not needed
     * @private
     * @param {Boolean} - to load new data or previosuly fetched data
     * @param {Boolean} - sorting is started
     * @memberof searchResults
     */
    _handleNonPersistentSearch: function (blnLoadData, blnSort) {
      var context = this;
      var searchQuery = $.extend(true, {}, context.searchQuery),
        srDeferred = $.Deferred(),
        deferred = $.Deferred(),
        size = searchResultsHelper.getSearchPaginationSize();


      if (context.searchQuery.q === "t0") {
        const srContext = searchResultsHelper.getSrContext();
        const taggedQuery = utilities.buildAliasQuery(srContext.data.patents, {
          documentId: 'guid',
          source: 'type'
        });
        searchQuery.q = taggedQuery;
      }

      context._getQueryCounts(searchQuery, deferred);
      // set offset search size (20000 results)
      var prefetchSize = searchResultsPrefetchHelper.doPrefetch(context.sorts.ui, context.filters) ? size + constants.SEARCH_PREFETCH_PAGE_SIZE : size;

      var sort = context.sorts.solr.sortStr || context.sortStr;



      var resultCount = context.isCollectionSearch ? prefetchSize : searchResultsSortHelper._fetchPageCountForCustomSortOrFilter(prefetchSize, searchResultsHelper.isUISortOrFilter(context.sorts, context.filters));



      var payload = searchResultsDataHelper.createPayload(searchQuery, resultCount, sort);

      // Fixed for DE10007 and DE 10008
      if (payload.query && payload.query.termHighlights) {
        delete payload.query.termHighlights;
      }

      // searchWithCountsStarted is set to false ,because the non-persitent search like from collection gadget is triggered.
      windowManager.getWindow().SESSION.searchWithCountsStarted = false;

      serviceManager.exec({
        url: services.getUrl('searchResults.querySearch'),
        params: JSON.stringify(payload),
        type: 'POST',
        contentType: 'application/json; charset=UTF-8',
        timeout: 120000,
        success: srDeferred.resolve,
        error: srDeferred.reject,
        notification: false
      });


      if (context.searchQuery.hasOwnProperty('queryId')) {
        delete context.searchQuery.id;
      }

      context.queryId = null;

      srDeferred.promise().then(context.getDataResponse.bind(this, blnLoadData), context.errorDataResponse.bind(this));
      return srDeferred.promise();
    },

    /**
     * Renders the grid with the latest session data and and binds the listeners to the grid
     * @private
     * @memberof searchResults
     */
    renderData: function () {
      var context = this;
      var intStartTime = new Date().getTime(),
        strMetricId = logManager.getUniqueId();

      context.renderDone = false;

      // Clear the print collection
      context.getSelectedDocumentRows([]);

      context._renderConfig();
      context.renderGrid();

      context._bindGridListeners();
      context._bindRowClickListeners();

      searchResultsPreferenceHelper.applyPreferences();

      context._triggerGridClickEvent();

      logManager.recordMetric({
        type: 'Gadget',
        title: context.widgetName,
        id: strMetricId,
        key: 'UI-searchResults',
        action: 'read',
        start: intStartTime
      });
      logManager.clearUniqueId();
    },

    /**
     * It handles error date response from Solr
     * @private
     * @param {Boolean} - sorting is started
     * @param {Object} - Solr response Object
     * @param {String} - status from error data response
     * @memberof searchResults
     */
    errorDataResponse: function (response, textStatus) {
      var context = this;
      context._hideLoader();
      //US557543 Removed sorting condition blnSort for standardization
      const errorText = response.status === 429 && response.responseJSON && response.responseJSON.message !== 'Too many requests' || response.status === 422 ? response.responseJSON.message : constants.NON_SQM_ERROR_TEXT;

      windowManager.getWindow().SESSION.searchResults = {};

      if (textStatus === 'abort') {
        context._showLoader();
      } else {
        context.element.find('.grid').html('<div class="errormessage">' + errorText + '</div>');

        searchResultsHelper.sqmSendNotification(errorText);
      }

      messageManager.send({
        action: 'MESSAGE-no-search-results',
        options: { error: true }
      });
      searchResultsGreyBarHelper.updatePaging();
    },

    /**
     * It handles search error response
     * @private
     * @param {Object} - error response Object
     * @memberof searchResults
     */
    _handleSearchError: function (searchError) {
      var context = this;
      context._clear();
      context.element.find('.visibleResults').hide();
      context.element.find('#search-results-export-btn').prop('disabled', true);
      if (searchError) {
        messageManager.send({
          action: 'MESSAGE-no-search-results',
          options: { error: true }
        });
        searchResultsHelper.sendNotificationForQueryError(searchError.errorMessage);
        windowManager.getWindow().SESSION.searchResults = {};
        context.element.find('.resultInfo').hide();
        context.element.find('.grid').html('<div class="errormessage"> Query Error : ' + searchError.errorMessage + '</div>');
        //alert screen reader of search errors
        setTimeout(function () {
          liveRegion.text('Query Error : ' + searchError.errorMessage);
        }, 0);

      }
    },

    /**
     * It handles search API call suceess response
     * @private
     * @param {Boolean} - to load new data or previosuly fetched data
     * @param {Object} - response Object
     * @param {Boolean} - is UI Sort or Filter is applied
     * @param {Integer} - page size
     * @memberof searchResults
     */
    _handleSearchResponse: function (blnLoadData, response, isUIOrSortFilter, size) {
      var context = this,
        pageSize = parseInt(searchResultsHelper.fetchPageCount.call(context));
      windowManager.getWindow().SESSION.searchResults = windowManager.getWindow().SESSION.searchResults || {};
      context.totalFilteredResults = response.numberOfFamilies;
      context.element.find('.resultInfo').show();
      context.element.find('#search-results-export-btn').prop('disabled', response.numberOfFamilies === 0);

      response = typeof response === 'string' ? JSON.parse(response) : response;

      if (blnLoadData) {
        context.totalGroupedResults = response.numberOfFamilies;
      }

      if ((context.searchQuery.q === 't0' || context.searchQuery.ignorePersist) && response.totalResults) {
        context.totalResults = context._getPreferences('docFamilyFiltering') === 'noFiltering' ? response.numFound : response.numberOfFamilies;
      }

      /* Only update the session data if blnLoadData is false so we don't end up updating it with
          bad data (ex: opening browser window with families expanded)
      */
      if (blnLoadData) {
        searchResultsDataHelper.updateSRSessionData(response, context.totalResults);
      }

      var cachedPatents = [];
      // if blnLoadData is not false.. do not update the cache since its already updated..
      if (blnLoadData !== false && !isUIOrSortFilter && searchResultsPrefetchHelper.doPrefetch(context.sorts.ui, context.filters, context.lastbuttonClicked)) {
        let getCachedPatentsResponse = searchResultsHelper.getCachedPatentsFromResponse('next', response, [], searchResultsHelper.getNextStart(), searchResultsHelper.isLastPageLoaded(response.patents));
        cachedPatents = getCachedPatentsResponse.cachedPatents;
        response = getCachedPatentsResponse.response;
      }

      context.data = response;
      context._updateContextDataHighlights(response);

      context._resetOrUpdateSRContext(context.newSearch, pageSize, response.patents.length);

      if (windowManager.getWindow().estCurrentPage === 'estbrowser' && !blnLoadData) {// Change sort in Browser window then it should be a new Search
        context.newSearch = false;
      }

      if (response && response.query) {
        windowManager.getWindow().SESSION.searchResults.documentFilter = response.query.id;
      }

      windowManager.getWindow().SESSION.searchResults.data = context.data;

      //polling to address the race condition where counts response comes after searchWithBEFamily.
      //This approach was chosen to avoid major code refactor.
      if (windowManager.getWindow().SESSION.searchWithCountsStarted && !hitTermsHelper.getHittermsSession().termHighlights) {
        context._startPollingForTermHighlights(context.data.patents, cachedPatents, isUIOrSortFilter, response, size);
      } else {
        searchResultsHittermHelper.highlightTextWithTermHighlights(context.data.patents);
        context._handleSearchResponseWithHighlights(cachedPatents, isUIOrSortFilter, response, size);
      }
    },
    /**
     * If the termhighlights are not available (when searchWithBEFamily returns before counts), this method keeps polling till counts
     * called is returned and then rendered the results in grid. This happens mainly when there are less no. of results returned.
     * @param {*} patents
     * @param {*} cachedPatents
     * @param {*} isUIOrSortFilter
     * @param {*} response
     * @param {*} size
     */
    _startPollingForTermHighlights: function (patents, cachedPatents, isUIOrSortFilter, response, size) {
      var interval = 10,
        context = this;
      var waitForTermHighlights = setInterval(function () {
        if (hitTermsHelper.getHittermsSession().termHighlights) {
          clearInterval(waitForTermHighlights);
          searchResultsHittermHelper.highlightTextWithTermHighlights(patents);
          context._handleSearchResponseWithHighlights(cachedPatents, isUIOrSortFilter, response, size);
          searchResultsHittermHelper.setCssRuleForHitTerm();
        } else if (windowManager.getWindow().SESSION.searchWithCountsStarted === false) {
          clearInterval(waitForTermHighlights);
        }
      }, interval);
    },
    /**
     * Process or handle the search response after the highlight/hit terms span tags are processed.
     * @param {*} cachedPatents
     * @param {*} isUIOrSortFilter
     * @param {*} response
     * @param {*} size
     */
    _handleSearchResponseWithHighlights: function (cachedPatents, isUIOrSortFilter, response, size) {
      var context = this;
      //If it is a new Search
      context._handleNewSearch(cachedPatents);

      if (isUIOrSortFilter && context._getPreferences('searchPagination') === 'manual' && windowManager.getWindow().SESSION.searchResults.cachedPage) {//No caching for Manual mode when Custom sort n filter is applied
        windowManager.getWindow().SESSION.searchResults.cachedPage.patents = [];
      }

      searchResultsNoteTagHelper.updateNotesAndTagDetails(isUIOrSortFilter, response, size);
      context._setLiveRegionTextAfterResponse(context.filters, context.totalResults);

      windowManager.getWindow().SESSION.searchResults.totalResults = context.totalResults;
      windowManager.getWindow().SESSION.searchResults.searchType = context.searchQuery.searchType;

      context._handleBrowseSearch(response.numFound);

      // setting flag here for metric
      context.setDocumentWasOpenedMetricFlag(true);

      // let other gadgets know that SR has loaded with data
      context._sendMessage('MESSAGE-searchResults-data-loaded');

      //metric for searchResultsReturned
      AnalyticsService.trackEvent(PAIPConstant.EVENT_SEARCH_RESULTS_RETURNED, {
        lNum: utilities.cleanLNumber(windowManager.getWindow().SESSION.searchResults.lNumber),
        queryId: windowManager.getWindow().SESSION.searchResults.searchQuery.id,
        text: windowManager.getWindow().SESSION.searchResults.searchQuery.q,
        resultCount: windowManager.getWindow().SESSION.searchResults.totalResults,
        querySource: windowManager.getWindow().SESSION.searchResults.searchQuery.querySource
      });
    },

    /**
     * Updates the live region text after the results are returned.
     * @private
     * @param filters - filters applied
     * @param totalResults - no of results
     * @memberof searchResults
     */
    _setLiveRegionTextAfterResponse: function (filters, totalResults) {
      setTimeout(function () {
        if (searchResultsHelper.isUIFilterApplied(filters)) {
          liveRegion.text(totalResults + ' Search Results have loaded with custom filters(s) applied.');
        } else {
          liveRegion.text(totalResults + ' Search Results have loaded with no custom filters(s) applied.');
        }
      });
    },

    /**
     * It handles Browse Search which opens Browser window
     * @private
     * @param {Integer} - total results found from counts call response
     * @memberof searchResults
     */
    _handleBrowseSearch: function (numFound) {
      var context = this,
        winSearchResults = windowManager.getWindow().SESSION.searchResults;
      if (context.searchOption === 'browse') {
        context._populateCurrentDocument(winSearchResults.data.patents[0]);
        winSearchResults.patentIndex = "id_0";
        searchResultsHelper.setUniqueIds(winSearchResults.data.patents);
        if (numFound > 0) {
          searchResultsBrowserHelper.openBrowserWindow(context.westbrowser);
        }
        context.searchOption = "";
      }
    },

    /**
     * It populates currently being viewed document into SESSION
     * @private
     * @param {Object} - patent Object
     * @memberof searchResults
     */
    _populateCurrentDocument: function (patent) {
      if (patent) {
        windowManager.getWindow().SESSION.currentDocumentBeingViewed = {
          documentId: patent.guid,
          type: patent.type,
          queryId: searchResultsHelper.getQueryId(patent.queryId),
          docSize: patent.documentSize,
          docIndex: patent.rowNumber,
          uniqueId: patent.uniqueId,
          imageLocation: patent.imageLocation,
          pageSetsImageLocation: patent.pageSets ? patent.pageSets[0] ? patent.pageSets[0].imageLocation : null : null
        };
      }
    },

    /**
     * It updates Prev or Next start , reset SearchResults SESSION data  as well as SearchResultsManager Model Object
     * @param {Boolean} newSearch
     * @memberof searchResults
     */
    _resetOrUpdateSRContext: function (newSearch, pageSize, patentLength) {
      if (newSearch) {
        // to reset if user changes page size
        searchResultsHelper.resetResultLength();
        searchResultsHelper.resetPageIndex();
        searchResultsHelper.setResultOffset(0);
        searchResultsHelper.setResultLength(patentLength, 'next');

        let nextStart = pageSize;
        searchResultsHelper.setNextStart(nextStart);
        searchResultsHelper.setPrevStart(0);
      }
      searchResultsHelper.setPrevStart(searchResultsHelper.getPrevStart());
      searchResultsHelper.setNextStart(searchResultsHelper.getNextStart());
    },

    /**
     * It handles New Search which always fetches data from Solr/API
     * @private
     * @param {Object} - Cached Patents Object
     * @memberof searchResults
     */
    _handleNewSearch: function (cachedPatents) {
      var context = this;
      if (context.newSearch) {
        if (searchResultsPrefetchHelper.doPrefetch(context.sorts.ui, context.filters)) {
          var prefetchNStart = searchResultsHelper.getNextStart() + constants.SEARCH_PREFETCH_PAGE_SIZE;

          if (context._getPreferences('docFamilyFiltering') === 'noFiltering' && prefetchNStart >= context.totalResults || context._getPreferences('docFamilyFiltering') !== 'noFiltering' && prefetchNStart >= context.totalGroupedResults) {
            prefetchNStart = -1;
          }

          searchResultsHelper.updateCachedPage(cachedPatents, searchResultsHelper.getPrevStart(), prefetchNStart, searchResultsHelper.getNextStart());
        } else if (windowManager.getWindow().SESSION.searchResults && windowManager.getWindow().SESSION.searchResults.cachedPage) {
          windowManager.getWindow().SESSION.searchResults.cachedPage.patents = [];
        }

        context.data.patents = searchResultsHelper.setMetaDataToSRData(context.data.patents, 0, windowManager.getWindow().SESSION.search ? windowManager.getWindow().SESSION.search.queryId : 0);
      }

    },

    /**
     * It updates termHighlights into Context
     * @private
     * @param {Object} - API response
     * @memberof searchResults
     */
    _updateContextDataHighlights: function (response) {
      var context = this;
      if (context.highlight && context.highlight.length > 0) {
        context.data.termHighlights = context.highlight;
      }
      //when we get data from session, set the context.hightlight (browser view)
      if (!context.newSearch && response.termHighlights && response.termHighlights.length > 0) {
        context.highlight = response.termHighlights;
      }
    },

    /**
     * It updates total Result count into SESSION based on search type like t0/C#/UISortFilter applied
     * @private
     * @param {Boolean} - Is UI Sort or Filter is applied
     * @param {Object} - Search Error Obj from Solr/API
     * @param {Boolean} - To load new data or previously fetched data
     * @param {Object} - API response
     * @memberof searchResults
     */
    _updateResultCount: function (isUIOrSortFilter, searchError, blnLoadData, response) {
      var context = this;
      //If UI Sort or Filter does not exist
      if (!isUIOrSortFilter) {
        context.totalResults = windowManager.getWindow().SESSION.resultCount; //Header Click sort change from UI to Solr should overwrite 10K with actual result
        windowManager.getWindow().SESSION.searchResults.sortedPatentData = context.sortedPatentData = []; //clear sortedPatentData if solr only sort is selected
      } else if (blnLoadData && !searchError && response.patents) {
        windowManager.getWindow().SESSION.searchResults.sortedPatentData = context.sortedPatentData = $.extend(true, [], response.patents); // Take the original data for Custom sort n filter overlay drop down list
      }

      if (context.searchQuery && context.searchQuery.q === 't0' || context.isCollectionSearch) {
        windowManager.getWindow().SESSION.resultCount = context.resultCount = context.totalResults = context._getPreferences('docFamilyFiltering') === 'noFiltering' ? response.numFound : response.numberOfFamilies; //For TD and UDC close and Open SR in Browser Window
      } else if (context.currentPatent) {
        context.totalResults = context._getPreferences('docFamilyFiltering') === 'noFiltering' ? response.numFound : response.numberOfFamilies;
        windowManager.getWindow().SESSION.resultCount = context.resultCount = response.patents.length;
      }

      //Update totalResults to the response query
      if (!searchError && context._getPreferences('showResults') === constants.SHOWRESULTS_LIMIT && context.searchOption === 'search') {
        if (response.totalResults) {
          response.query.numResults = response.totalResults;
        }
      }
    },

    /**
     * It Handles Search API sucess callback
     * @private
     * @param {Boolean} - To load new data or previously fetched data
     * @param {Object} - API response
     * @memberof searchResults
     */
    getDataResponse: function (blnLoadData, response) {
      var context = this;
      var searchError = response.error,
        size = searchResultsHelper.getSearchPaginationSize(),
        strMetricId = logManager.getUniqueId(),
        intStartTime = new Date().getTime(),
        winSESSION = windowManager.getWindow().SESSION,
        isUIOrSortFilter = searchResultsHelper.isUISortOrFilter(context.sorts, context.filters);

      if (!searchError && blnLoadData) {//retain total families for close/open SR
        winSESSION.searchResults.resultFamilies = response.numberOfFamilies;
      }

      context._updateResultCount(isUIOrSortFilter, searchError, blnLoadData, response);

      //For Document Viewer Navigation
      windowManager.getWindow().SESSION.searchResults.sort = context.sorts;

      logManager.recordMetric({
        type: 'Gadget',
        title: context.widgetName,
        id: strMetricId,
        key: 'API-searchResults-data',
        action: 'read',
        start: intStartTime
      });

      context._hideLoader();

      if (!searchError && response && response.patents) {
        context._handleSearchResponse(blnLoadData, response, isUIOrSortFilter, size);
      } else {
        context._handleSearchError(searchError);
      }
      if (!context.sortingStarted) {
        // context.currentPatent will be defined in case navigation is from Tagged Documents gadget
        context.element.find('.controls .resultNumber').text(context.resultCount);
        if (!context.currentPatent) {
          if (context.totalResults === 0) {
            messageManager.send({
              action: 'MESSAGE-hitTrems-clear'
            });
          }
        }

        searchResultsHittermHelper.setHighlightBar(context.element);
        searchResultsHittermHelper.setCssRuleForHitTerm();
      }
    },

    /**
     * @description Issues API call to fetch 1st page set of data
     * @public
     * @param {Boolean} blnLoadData
     * @param {Boolean} blnSort
     * @returns {Object} promise
     * @memberof searchResults
     */
    getSearchResults: function (blnLoadData, blnSort) {
      var context = this;
      var sort = context.sorts.solr.sortStr || context.sortStr,
        srDeferred = $.Deferred(),
        size = searchResultsHelper.getSearchPaginationSize(),
        isUiSortOrFilter = searchResultsHelper.isUISortOrFilter(context.sorts, context.filters);

      // set offset search size (20000 results)
      var prefetchSize = searchResultsPrefetchHelper.doPrefetch(context.sorts.ui, context.filters) ? size + constants.SEARCH_PREFETCH_PAGE_SIZE : context.isCollectionSearch ? 100 : size;

      var resultCount = searchResultsSortHelper._fetchPageCountForCustomSortOrFilter(prefetchSize, isUiSortOrFilter);

      if (context.ajaxRequest) {//issued getMoreSearchData request should be ignored
        searchResultsManager.cancelAjaxCalls(context);
      }

      var payload = searchResultsDataHelper.createPayloadForInitialSearch(context.searchQuery, resultCount, sort, isUiSortOrFilter, context.searchOption);
      if (context._getPreferences('showResults') !== constants.SHOWRESULTS_LIMIT || context.searchOption !== 'search' && context.searchOption !== 'facetSearch') {
        context.searchQuery.ignorePersist = true;
      }

      windowManager.getWindow().SESSION.searchResults.requestComplete = false;

      context.summaryXHR = serviceManager.exec({
        url: services.getUrl('searchResults.data'),
        params: JSON.stringify(payload),
        type: 'POST',
        contentType: 'application/json; charset=UTF-8',
        timeout: 300000,
        success: srDeferred.resolve,
        error: srDeferred.reject,
        notification: false
      });
      context.searchQuery.ignorePersist = false;
      srDeferred.promise().then(context.getDataResponse.bind(context, blnLoadData), context.errorDataResponse.bind(context));
      messageManager.send({
        action: "MESSAGE-documentViewer-clear-text"
      });
      return srDeferred.promise();
    },

    _createContextualMenu: function () {
      if (!this.contextMenuColumn) {
        this.contextMenuColumn = new ContextualMenu(searchResultsContextMenuConfig.get('columnMenu'), this.element.find('.contentgrid'));
      }
    },

    setDocumentWasOpenedMetricFlag(boolean) {
      const context = this;
      context.documentWasOpenedMetricFlag = !!boolean;
    }
  });
});
//# sourceMappingURL=searchResults.js.map
