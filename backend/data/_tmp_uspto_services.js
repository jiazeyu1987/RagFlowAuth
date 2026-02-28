define([
'common/settings'],
function (settings) {

  "use strict";
  var basePaths = {
      _default: settings.CONTEXT,
      _imageHost: window.imageHost,
      _DEF_CPC: 'http://ptoweb.uspto.gov:8081/',
      _DEF_IPC: 'https://www.wipo.int/',
      _DEF_USPC: 'http://ptoweb.uspto.gov/'
    },

    replaceParams = function (url, params) {
      for (var key in params) {
        if (params.hasOwnProperty(key)) {
          const regex = '#' + key + '#';
          const replace = new RegExp(regex, 'g');

          url = url.replace(replace, params[key]);
        }
      }
      return url;
    },

    urls = {
      index: {
        data: window.CONFIG.mock ? 'pages/index/index_data.json' : basePaths._default + '',
        newWorkspace: basePaths._default + 'cases/#caseId#'
      },
      help: {
        data: window.CONFIG.mock ? 'gadgets/help/help_data.json' : basePaths._default + 'help/content'
      },
      search: {
        fitCountries: basePaths._default + 'fitConfig',
        layoutConfig: 'gadgets/search/search_layoutConfig.json',
        databases: window.CONFIG.mock ? 'gadgets/search/search_databases.json' : basePaths._default + '',
        externalCounts: basePaths._default + 'searches/externalQuery/#queryType#/counts'
      },
      searchHistory: {
        layoutConfig: 'gadgets/searchHistory/searchHistory_layoutConfig.json',
        data: window.CONFIG.mock ? 'gadgets/searchHistory/searchHistory_data.json' : basePaths._default + 'cases/#caseId#/queries',
        undo: basePaths._default + 'cases/#caseId#/queries/restore',
        remove: basePaths._default + 'cases/#caseId#/queries/#action#'
      },
      searchResults: {
        layoutConfig: 'gadgets/searchResults/searchResults_layoutConfig.json',
        databases: window.CONFIG.mock ? 'gadgets/search/search_databases.json' : basePaths._default + '',
        querySearch: basePaths._default + 'searches/searchWithBeFamily',
        data: window.CONFIG.mock ? 'gadgets/searchResults/searchResults_data_8.json' : basePaths._default + 'searches/searchWithBeFamily',
        numFound: window.CONFIG.mock ? 'gadgets/searchResults/searchResults_data_8.json' : basePaths._default + 'searches/counts',
        moreData: window.CONFIG.mock ? 'gadgets/searchResults/searchResults_data_8.json' : basePaths._default + 'searches/searchWithBeFamily',
        image: basePaths._default + 'image/convert?url=#imageLocation#/#imageFileName#',
        gridPrint: basePaths._default + '2.0/cases/#caseId#/value/#printKey#',
        gridPrintPdfUrl: basePaths._default + '2.0/cases/#caseId#/value/#printKey#.pdf?shouldDownload=#shouldDownload#',
        viewed: basePaths._default + '2.0/patents/#caseId#/#action#',
        termsExpansionCheck: basePaths._default + 'tf/termsExpansionCheck',
        hitTermFrequency: basePaths._default + 'tf/termcounts?term=#term#&sort=#sort#&sortOrder=#sortOrder#&maxResult=#maxResult#&aliases=#aliases#',

        citationSearchOverlay: 'features/citationSearchOverlay/citationSearchOverlay_config.json'
      },
      taggedDocument: {
        config: 'gadgets/taggedDocument/taggedDocument_config.json',
        layoutConfig: 'gadgets/taggedDocument/taggedDocument_layoutConfig.json',
        metadata: window.CONFIG.mock ? 'gadgets/taggedDocument/taggedDocument_metadata.json' : basePaths._default + 'cases/#caseId#/canvasgroups',
        listData: basePaths._default + 'cases/#caseId#/patents',
        tagListDefaultsDefaultTagGroupNames: 'features/tagList/tagList_defaults-DefaultTagGroupNames.json',
        deletePatents: basePaths._default + 'cases/#caseId#/canvasgroups/patents',
        deleteAll: basePaths._default + 'cases/#caseId#/canvasgroups',
        createOrUpdateTags: basePaths._default + 'cases/#caseId#/canvasgroups/#action#'
      },
      notesViewer: {
        layoutConfig: 'gadgets/notesViewer/notesViewer_layoutConfig.json',
        data: window.CONFIG.mock ? 'gadgets/notesViewer/notesViewer_data.json' : basePaths._default + 'cases/#caseId#/patentnotes',
        createNote: basePaths._default + 'cases/#caseId#/patentnotes',
        updateNote: basePaths._default + 'cases/#caseId#/patentnotes/#patentNoteId#',
        deleteNotes: basePaths._default + 'cases/#caseId#/patentnotes',
        updateNoteHighlightColors: basePaths._default + 'cases/#caseId#/patentnotes/highlightcolors',
        saveNotes: basePaths._default + 'print/patentNotes'
      },
      hitTerms: {
        layoutConfig: 'gadgets/hitTerms/hitTerms_layoutConfig.json',
        data: 'gadgets/hitTerms/hitTerms_data.json',
        getHighlights: basePaths._default + '2.0/queryhighlight/get/#queryId#',
        updateHighlights: basePaths._default + '2.0/queryhighlight/update/#queryId#'
      },

      sampleGadget: {
        data: 'gadgets/sampleGadget/sampleGadget_data.json'
      },
      sampleGridGadget: {
        config: 'gadgets/sampleGridGadget/sampleGridGadget_config.json',
        data: 'gadgets/sampleGridGadget/sampleGridGadget_data.json'
      },
      sampleGadgetDelayed: {
        data: 'gadgets/sampleGadgetDelayed/sampleGadgetDelayed_data.json'
      },
      user: {
        data: window.CONFIG.mock ? 'common/user.json' : basePaths._default + 'users/me/session',
        getPreference: basePaths._default + 'users/preferences/#preferenceCode#',
        savePreferece: basePaths._default + 'users/preferences',
        clearUserData: basePaths._default + 'users/#userSessionId#/softdelete',
        updateUserSessionLastUpdateDate: basePaths._default + 'users/lastUpdateDate/#userSessionId#'
      },
      preferences: {
        get: basePaths._default + 'users/#employeeId#/value/#key#',
        set: basePaths._default + 'users/#employeeId#/value/#key#',
        remove: basePaths._default + 'users/#employeeId#/value/#key#'
      },
      // TODO: remove unused code like highlights.getQueryHighlightData, et al.
      highlights: {
        data: window.CONFIG.mock ? 'gadgets/documentViewer/documentViewer_data_1.json' : basePaths._default +
        'patents/highlight/#docId#?queryId=#queryId#&source=#source#&includeSections=#includeSections#&uniqueId=#uniqueId#',
        sections: basePaths._default + 'patents/highlightSections/#docId#?queryId=#queryId#&source=#source#&cachescope=private&cacheage=300',
        config: 'features/highlightManager/highlightTable_config.json',
        getQueryHighlightData: basePaths._default + '2.0/queryhighlight/all/#queryId#',
        getQueryHighlightDataForList: basePaths._default + '2.0/queryhighlight/all',
        deleteQueryHighlightData: basePaths._default + '2.0/queryhighlight/delete/#queryId#',
        saveQueryHighlightData: basePaths._default + '2.0/queryhighlight/save/#queryId#',
        saveAllQueryHighlightData: basePaths._default + '2.0/queryhighlight/saveall/#queryId#'
      },
      documentViewer: {
        layoutConfig: 'gadgets/documentViewer/documentViewer_layoutConfig.json',
        imageViewerPrintAndSave: basePaths._default + 'patents/#patentId#/#printKey#.pdf?caseId=#caseId#&dataSource=#dataSource#&imageSections=#imageSections#&invertImages=#invertImages#&shouldDownload=#shouldDownload#',
        textViewerPrint: basePaths._default + '2.0/cases/#caseId#/value/#printKey#',
        textViewerPrintPdfUrl: basePaths._default + '2.0/cases/#caseId#/value/#printKey#.pdf?shouldDownload=#shouldDownload#',
        image: basePaths._default + 'image/convert?url=#imageLocation#/#imageFileName#'
      },
      layouts: {
        create: basePaths._default + 'users/#userGuid#/layout',
        update: basePaths._default + 'users/#userGuid#/layout/#layoutId#',
        get: basePaths._default + 'users/#layoutId#/layout',
        getAll: basePaths._default + 'users/#userGuid#/layout/#layoutType#',
        remove: basePaths._default + 'users/#layoutId#/layout'
      },
      print: {
        createImageViewerPDF: basePaths._default + 'print/imageviewer',
        config: 'features/printPreferences/printPreferences_config.json',
        getJobs: basePaths._default + 'print/print-process',
        savePDF: basePaths._default + 'print/save/#fileName#',
        printPDF: basePaths._default + 'print/print/#fileName#',
        createSearchHistoryPDF: basePaths._default + 'print/searchhistory'
      },
      patentRefUrls: {
        usci_baseUrl: "https://www.uspto.gov/web/patents/classification/uspc",
        usc_baseUrl: "https://www.uspto.gov/web/patents/classification/uspc",
        cpc_baseUrl: "https://www.uspto.gov/web/patents/classification/cpc/html/cpc-",
        ipc_baseUrl: "http://ptoweb:8081/international/ipc/ipc8/"
      },
      classifications: {
        getClassificationInfo: basePaths._default + 'classifications/classificationDetails?type=#type#&name=#classificationName#',
        getInternalClassificationPageUrl: 'classification.html?type=#type#&cls=#clsVal#&bsc=#bscVal#&ipcVersion=#ipcVersion#'
      },
      customSortsFilters: {
        defineConfig: 'features/customSortsFilters/customSortsFilters_define_config.json',
        manageConfig: 'features/customSortsFilters/customSortsFilters_manage_config.json',
        manageData: basePaths._default + '2.0/user/preferences/#userId#/#gadgetType#',
        saveCustomSortFilter: basePaths._default + '2.0/user/preferences',
        getLastUsedSortFilter: basePaths._default + '2.0/user/preferences/#userId#',
        deleteCustomSortFilter: basePaths._default + '2.0/user/preferences/#userId#/#prefId#'
      }

    };
  /**
   * The map of all the service urls.
   * TODO - Need to add all url end points.
   * @namespace services
   */

  return {
    urls: urls,
    replaceParams: replaceParams,
    getUrl: function (path, params) {
      var context = this,
        url;
      $.each(path.split('.'), function (index, elem) {
        if (index === 0) {
          url = context.urls[elem] || null;
        } else {
          url = url ? url[elem] : null;
        }
        if (!url) {
          return false;
        }
      });
      if (params && url) {
        url = this.replaceParams(url, params);
      }
      return url;
    }
  };
});
//# sourceMappingURL=services.js.map
