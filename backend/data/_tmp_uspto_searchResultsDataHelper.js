/**
 * Created by dkovi on 7/16/2018.
 */
define([
'jquery.plugins',
'framework/windowManager',
'framework/logManager',
'common/constants',
'features/tagManager/tagManager',
'features/notesManager/notesManager',
'gadgets/searchResults/searchResultsGridHelper',
'gadgets/searchResults/searchResultsHelper',
'gadgets/searchResults/searchResultsSortHelper',
'gadgets/searchResults/searchResultsFindHelper',
'gadgets/searchResults/searchResultsHittermHelper',
'gadgets/searchResults/searchResultsGreyBarHelper',
'gadgets/searchResults/searchResultsPreferenceHelper',
'common/_utilities'],
function (
$,
windowManager,
logManager,
constants,
tagManager,
notesManager,
searchResultsGridHelper,
searchResultsHelper,
searchResultsSortHelper,
searchResultsFindHelper,
searchResultsHittermHelper,
searchResultsGreyBarHelper,
searchResultsPreferenceHelper,
utilities)
{
  'use strict';

  return {
    /**
     * @description @description Based on Family Filter settings and search Type , it constructs payload for initial API Search Call and updates the page size base on ui sort n filter settings
     * @param {Object} UserPreferences
     * @param {Object} searchQuery
     * @param {Integer} resultCount
     * @param {Object} sort
     * @param {Boolean} isUiSortOrFilter
     * @param {String} searchOption
     * @method createPayloadForInitialSearch
     * @returns payload
     */
    createPayloadForInitialSearch: function (searchQuery, resultCount, sort, isUiSortOrFilter, searchOption) {
      var srContext = searchResultsHelper.getSrContext();
      if (searchQuery.facets) {
        delete searchQuery.facets;
      }
      var payload = this.createPayload(searchQuery, resultCount, sort, 0, searchQuery);

      delete payload.query.fromtaggedlNumber;
      if (srContext._getPreferences('showResults') === constants.SHOWRESULTS_LIMIT && (searchOption === 'search' || searchOption === 'facetSearch')) {
        payload.limit = parseInt(getPreferences('limit'));
        if (payload.limit < resultCount) {
          payload.pageCount = payload.limit;
          if (isUiSortOrFilter) {
            payload.pageCount = constants.CUSTOM_SORT_PAGE_SIZE;
          }
        }
        payload.query.ignorePersist = true;
        payload.numFoundRequired = true;
        payload.limitsRequired = true;
      }

      delete payload.query.fromtaggedlNumber;

      return payload;

    },

    /**
     * @description Based on Family Filter settings and search Type , it constructs payload for API Search Call
     * @param {Object} UserPreferences
     * @param {Object} searchQuery - the query to extract data from for the payload
     * @param {Integer} resultCount
     * @param {Object} sort
     * @param start - start position for payload message, defaults to 0
     * @param executedQuery - the query to attach to the payload (defaults to searchQuery)
     * @method createPayload
     * @memberof searchResultsDataHelper
     * @returns payload
     */
    createPayload: function (searchQuery, resultCount, sort, start = 0, executedQuery = searchQuery) {
      var srContext = searchResultsHelper.getSrContext();
      let docFamilyFiltering = srContext._getPreferences('docFamilyFiltering'),searchType = searchQuery.searchType;
      let familyIdEnglishOnly = docFamilyFiltering === 'noFiltering' ? null : docFamilyFiltering === 'appNumFiltering' ? null : srContext._getPreferences('familyIdEnglishOnly'),
        familyIdFirstPreferred = docFamilyFiltering === 'noFiltering' ? null : docFamilyFiltering === 'appNumFiltering' ? searchType === constants.PRIORART ? srContext._getPreferences('appNumPriorFirstPreferred') : srContext._getPreferences('appNumInterferenceFirstPreferred') : srContext._getPreferences('familyIdFirstPreferred'),
        familyIdSecondPreferred = docFamilyFiltering === 'noFiltering' ? null : docFamilyFiltering === 'appNumFiltering' ? searchType === constants.PRIORART ? srContext._getPreferences('appNumPriorSecondPreferred') : srContext._getPreferences('appNumInterferenceSecondPreferred') : srContext._getPreferences('familyIdSecondPreferred'),
        familyIdThirdPreferred = docFamilyFiltering === 'noFiltering' ? null : docFamilyFiltering === 'appNumFiltering' ? null : srContext._getPreferences('familyIdThirdPreferred'),
        showDocPerFamilyPref = docFamilyFiltering === 'noFiltering' ? null : docFamilyFiltering === 'appNumFiltering' ? null : srContext._getPreferences('showDocPerFamilyPref');

      return {
        start: start,
        pageCount: resultCount,
        sort: decodeURI(sort),
        docFamilyFiltering: srContext._getPreferences('docFamilyFiltering'),
        searchType: searchQuery.searchType,
        familyIdEnglishOnly: familyIdEnglishOnly,
        familyIdFirstPreferred: familyIdFirstPreferred,
        familyIdSecondPreferred: familyIdSecondPreferred,
        familyIdThirdPreferred: familyIdThirdPreferred,
        showDocPerFamilyPref: showDocPerFamilyPref,
        queryId: 0,
        tagDocSearch: searchQuery.q === 't0',
        query: executedQuery
      };
    },

    /**
     * It updates Window Manager Search Results SESSION data
     * @param {Object} response
     * @param {Integer} totalResults
     * @memberof searchResultsDataHelper
     */
    updateSRSessionData: function (response, totalResults) {
      windowManager.getWindow().SESSION.searchResults.data = response;
      windowManager.getWindow().SESSION.searchResults.data.groupedResults = response.groupedResults;
      windowManager.getWindow().SESSION.searchResults.data.totalGroupedResults = response.numberOfFamilies;
      windowManager.getWindow().SESSION.searchResults.totalResults = totalResults;

    },

    /**
     * @description It creates payLoad for API search call
     * @param {Boolean} isCollectionSearch
     * @param {Boolean} isCollectionSearchData
     * @param [array] items
     * @param [array] tempPatentList
     * @method _populateIds
     * @memberof searchResultsDataHelper
     * @returns [array]
     */
    _populateIds: function (isCollectionSearch, isCollectionSearchData, items, tempPatentList) {
      if (isCollectionSearch) {
        if (isCollectionSearchData) {
          items.forEach(function (obj) {
            tempPatentList.forEach(function (tempObj) {
              if (obj.guid === tempObj.guid) {
                tempObj.id = obj.id;
              }
            });
          });
        }
      }
      return tempPatentList;

    },

    /**
     * Fetches the next set of data
     * performPrefetch bool - Do we prefetch data
     * position str - the current pointer direction
     * size int - the pagination size to use
     * return int - pointer position
     */
    _fetchData: function (performPrefetch, position, size) {
      var pointer = 0;
      var context = this;
      var srContext = searchResultsHelper.getSrContext();
      var totalResults = searchResultsHelper.getResultsByFamilyFiltering(srContext._getPreferences('docFamilyFiltering'), srContext.totalResults, srContext.totalGroupedResults);

      if (searchResultsHelper.isUISortOrFilter(srContext.sorts, srContext.filters)) {
        totalResults = srContext.data.patents.length;
      }

      if (performPrefetch) {
        pointer = context._getPrefetchPointer(position, srContext.lastbuttonClicked, totalResults);
      } else {
        if (position === 'next') {
          pointer = searchResultsHelper.getNextStart();
        } else if (position === 'previous') {
          pointer = searchResultsHelper.getPrevStart();
        }
      }
      return pointer;
    },

    /**
     * Get the pointer position when prefetching.
     * position str - the direction we are prefetching
     * lastbuttonClicked boolean - was the last button clicked to trigger this fetch
     * totalResults - the total number of results for the search
     * return INT pointer position in prefetch
     */
    _getPrefetchPointer: function (position, lastbuttonClicked, totalResults) {
      var pointer = 0;
      if (position === 'next') {
        if (lastbuttonClicked) {
          if (totalResults < constants.SEARCH_PREFETCH_PAGE_SIZE) {
            pointer = 0;
          } else {
            pointer = searchResultsHelper.getNextStart() - constants.SEARCH_PREFETCH_PAGE_SIZE;
          }
        } else {
          pointer = searchResultsHelper.getNextStart();
        }
      } else if (position === 'previous') {
        pointer = searchResultsHelper.getPrevStart() - constants.SEARCH_PREFETCH_PAGE_SIZE;
      }
      return pointer;
    },

    /**
     * Function to handle error response in the getMoreSearchData function's process
     * deferred {} - deferred that handles async for the calling function
     */
    gmdErrorDataResponse: function (deferred) {
      var sr_context = searchResultsHelper.getSrContext();
      // Code may reach here because of cancelAjaxCalls() along with regular errors.
      sr_context.ajaxRequest = null;
      sr_context.lastbuttonClicked = false;
      // enable navigation buttons
      searchResultsGreyBarHelper.enableNavigationButtons();
      sr_context.element.find('.loadingButton').hide();
      searchResultsGreyBarHelper.updateDisplayResultsCount();
      deferred.reject();
    },

    /**
     * Function to set the initial state of things for processing a "getMoreData" response object
     * resets page index and increases current page number when appropriate
     * sr_context - The searchResults Context to perform the page incrementation on.
     */
    _setInitialStateGMDResponse: function (sr_context, position, pointer) {
      if (sr_context.lastbuttonClicked) {
        searchResultsHelper.resetPageIndex();
      }

      if (sr_context._getPreferences('searchPagination') === 'manual' && position === 'next' && !sr_context.lastbuttonClicked && pointer !== 0 && sr_context.navigateDirection !== 'down') {
        sr_context.currentPageNumber = sr_context.currentPageNumber + 1;
      }
    },

    /**
     * Function to parse the getMoreResults response data into useable formats.
     * Adds proper highlights, metadata, note details, tag details, and sort to the patents.
     * response - The GetMoreData response we are parsing.  Will update the contents of the object itself.
     * sr_context - the searchResults context we are processing data for
     * startOfId -
     */
    _parseResponseData: function (response, sr_context, startOfId) {
      response.patents = searchResultsHittermHelper.highlightTextWithTermHighlights(response.patents);
      response.patents = searchResultsHelper.setMetaDataToSRData(response.patents, startOfId, response.query ? response.query.id : 0);

      //Update Note Details
      response.patents = notesManager._parseMapNoteDetails(response.patents);

      //Client sort if applies
      if (searchResultsHelper.isUISortOrFilter(sr_context.sorts, sr_context.filters)) {
        response.patents = searchResultsSortHelper._sortResultsUIAndSolr(sr_context.sorts, false, true, response.patents);
      }
    },

    /**
     * Function to update the next and prev start from a getMoreData call
     * sr_context - searchResults context we are processing data for
     * packagedData - object containing the following properties:
     *      position - direction the data fetch is occuring
     *      pointer - position of the data set
     *      response - the GetMoreData response object
     *      size -
     *      blnIsFirst -
     *      performPrefetch - boolean if we are performing a prefetch or not
     *      cachedPatents - the array of cached patents if any
     */
    _setPrevNextStart: function (sr_context, packagedData) {
      var position = packagedData.position;
      var pointer = packagedData.pointer;
      var response = packagedData.response;
      var size = packagedData.size;
      var blnIsFirst = packagedData.blnIsFirst;
      var performPrefetch = packagedData.performPrefetch;
      var cachedPatents = packagedData.cachedPatents;
      const context = this;
      let prevNextStartModel = {
        prevStart: searchResultsHelper.getPrevStart(),
        nextStart: searchResultsHelper.getNextStart()
      };

      // get prev/next start
      prevNextStartModel = searchResultsHelper.getPrevNextStart(prevNextStartModel, position, pointer, sr_context.data.patents, response.patents, sr_context.lastbuttonClicked);

      searchResultsHelper.setNextStart(prevNextStartModel.nextStart);
      searchResultsHelper.setPrevStart(prevNextStartModel.prevStart);

      if (performPrefetch) {
        const cachedPrevStart = context._getCachedPrevStart(size);
        const cachedNextStart = context._getCachedNextStart(size, blnIsFirst);
        searchResultsHelper.updateCachedPage(cachedPatents, cachedPrevStart, cachedNextStart, blnIsFirst ? searchResultsHelper.getNextStart() : searchResultsHelper.getPrevStart());
      }
    },

    /**
     * Function to update the page number in the window session and ensure the srContext grid navigates to the next page if needed
     * sr_context - the search results Context that we are updating
     * position - the direction of the pagination navigation
     */
    _updatePageNumber: function (sr_context, position) {
      if (sr_context._getPreferences('searchPagination') === 'manual') {
        sr_context.grid.options.grid.setActiveCell(0, 0);
        if (position === 'next' && !searchResultsHelper.areResultsDeallocated(sr_context.data.patents, sr_context.totalResults)) {
          sr_context.grid.options.paging.gridNavNext(searchResultsHelper.fetchPageCount.call(sr_context));
        }
        windowManager.getWindow().SESSION.searchResults['pageNum'] = sr_context.grid.options.paging.getGridNavState().pagingInfo.pageNum;
      }
    },

    /**
     * Function to handle the data response in the getMoreSearchData function's process
     * response {} - The data response from a searchResultsManager.getMoreData function call
     * gmdData {} - object containing the following attributes
     *      blnIsFirst -
     *      strMetricId - the ID for logging metrics
     *      intStartTime - the start time of the getMoreSearchData call for logging
     *      position - direction pointer is moving
     *      performPrefetch bool - was prefetch performed
     *      pointer - position of the pointer
     * deferred - the deferred being used for getMoreSearchData's response
     */
    gmdGetDataResponse: function (response, gmdData, deferred) {
      var sr_context = searchResultsHelper.getSrContext();
      var context = this;
      var blnIsFirst = gmdData.blnIsFirst,
        strMetricId = gmdData.strMetricId,
        intStartTime = gmdData.intStartTime,
        position = gmdData.position,
        performPrefetch = gmdData.performPrefetch,
        pointer = gmdData.pointer;

      logManager.recordMetric({
        type: 'Gadget',
        title: sr_context.widgetName,
        id: strMetricId,
        key: 'API-searchResults-data',
        action: 'read',
        start: intStartTime
      });

      var size = searchResultsHelper.getSearchPaginationSize();
      response = typeof response === 'string' ? JSON.parse(response) : response;
      intStartTime = new Date().getTime();
      context._setInitialStateGMDResponse(sr_context, position, pointer);
      var cachedPatents = [];

      if (performPrefetch) {
        const getCachedPatentsResponse = searchResultsHelper.getCachedPatentsFromResponse(position, response, sr_context.data.patents, searchResultsHelper.getNextStart(), sr_context.lastbuttonClicked);
        cachedPatents = getCachedPatentsResponse.cachedPatents;
        response = getCachedPatentsResponse.response;
      }

      // set start of id
      const startOfId = searchResultsHelper.getStartOfIdforResultData(position, pointer, sr_context.data.patents, response.patents.length, sr_context.lastbuttonClicked);
      sr_context.element.find('.loadingButton').hide();

      context._parseResponseData(response, sr_context, startOfId);
      searchResultsHelper.setResultLength(response.patents.length, position);

      // Limit Search result data
      sr_context.data.patents = searchResultsHelper.limitSRDataMemory(position, sr_context.data.patents, response.patents, sr_context.currentPageNumber);

      //This is needed because for UI sort n Fiter no more data fetching from API so ID's will not be changed
      if (searchResultsHelper.isUISortOrFilter(sr_context.sorts, sr_context.filters) && sr_context._getPreferences('searchPagination') === 'ondemand') {
        searchResultsHelper._setUniqueIdAndRowNums(sr_context.data.patents);
      }

      context._setPrevNextStart(sr_context, { position, pointer, response, size, blnIsFirst, performPrefetch, cachedPatents });

      searchResultsGridHelper.updateGridPaginationData(position, size);

      // scroll grid in such a way that last record of previous result is displayed in the last row
      sr_context.scrollGridAfterNewData(position, utilities.filteredItems(response.patents).length);

      //DO NOT REMOVE as this is addressing edge case scenario
      //Page Size 10/50 and total Results are 900 , go to 2nd page and go to last is giving blank grid since page count on the grid is not changed and grid is not re-rendered with new set of data
      if (sr_context._getPreferences('searchPagination') === 'manual' && size < constants.SEARCH_PREFETCH_PAGE_SIZE && utilities.filteredItems(sr_context.data.patents).length === size) {
        searchResultsGreyBarHelper.updatePaging();
      }
      // Update displaying results count and pagingInfo
      searchResultsGreyBarHelper.updateDisplayResultsCount();
      context._updatePageNumber(sr_context, position);
      searchResultsFindHelper.applyFindWithin(true);

      logManager.recordMetric({
        type: 'Gadget',
        title: sr_context.widgetName,
        id: strMetricId,
        key: 'UI-searchResults',
        action: 'read',
        start: intStartTime
      });

      logManager.clearUniqueId();

      context._gmdResponsePostProcessingSteps(sr_context, position, pointer, deferred);
    },

    /**
     * Function to preform the cleanup steps after processing a getMoreDataResponse
     * sr_context - the search results context we were processing data for
     * position - the direction the search was being performed in
     * pointer - the position of the pagination
     * deferred - the deferred object that we resolve to signal processing is done
     */
    _gmdResponsePostProcessingSteps: function (sr_context, position, pointer, deferred) {
      sr_context.ajaxRequest = null;

      // enable navigation buttons
      searchResultsGreyBarHelper.enableNavigationButtons();

      // reset last button clicked
      if (position === 'previous' || position === 'next' && pointer === 0) {
        sr_context.setLastButtonClicked(false);
      }
      //add CSS Rules for the terms that were just parsed from the latest data set
      searchResultsHittermHelper.setCssRuleForHitTerm();

      deferred.resolve();
      searchResultsPreferenceHelper.applyPreferences(true);
      windowManager.getWindow().SESSION.searchResults.requestComplete = true;
    },

    /**
     * Function to get the value of the previous start value
     * size - int the pagination size
     * @returns int the cached previous start value
     */
    _getCachedPrevStart: function (size) {
      if (searchResultsHelper.getSrContext().lastbuttonClicked) {
        if (searchResultsHelper.getPrevStart() < constants.SEARCH_PREFETCH_PAGE_SIZE) {
          return 0;
        } else {
          return searchResultsHelper.getPrevStart() - constants.SEARCH_PREFETCH_PAGE_SIZE;
        }
      } else {
        return searchResultsHelper.getNextStart() - size;
      }
    },

    /**
     * function to get the value of the next start value
     * size - int the pagination size
     * blnIsFirst -
     * returns int - the cached next start value
     */
    _getCachedNextStart: function (size, blnIsFirst) {
      if (searchResultsHelper.getSrContext().lastbuttonClicked) {
        return searchResultsHelper.getNextStart();
      } else if (blnIsFirst) {
        return searchResultsHelper.getNextStart() + constants.SEARCH_PREFETCH_PAGE_SIZE;
      } else {
        return searchResultsHelper.getNextStart() + size;
      }
    }

  };
});
//# sourceMappingURL=searchResultsDataHelper.js.map
