define(function () {

  const CONTEXTUAL_COMMON_COLORS_NOTES = [{
    label: 'Red',
    hexCode: '#ff6666',
    data: {
      action: 'colorChange',
      hexCode: '#ff6666'
    }
  },
  {
    label: 'Orange',
    hexCode: '#ffcc66',
    data: {
      action: 'colorChange',
      hexCode: '#ffcc66'
    }
  },
  {
    label: 'Yellow',
    hexCode: '#ffff33',
    data: {
      action: 'colorChange',
      hexCode: '#ffff33'
    }
  },
  {
    label: 'Green',
    hexCode: '#33ff33',
    data: {
      action: 'colorChange',
      hexCode: '#33ff33'
    }
  },
  {
    label: 'Blue',
    hexCode: '#66ccff',
    data: {
      action: 'colorChange',
      hexCode: '#66ccff'
    }
  },
  {
    label: 'Cyan',
    hexCode: '#00ffff',
    data: {
      action: 'colorChange',
      hexCode: '#00ffff'
    }
  },
  {
    label: 'Lavender',
    hexCode: '#ccccff',
    data: {
      action: 'colorChange',
      hexCode: '#ccccff'
    }
  },
  {
    label: 'Purple',
    hexCode: '#cc66ff',
    data: {
      action: 'colorChange',
      hexCode: '#cc66ff'
    }
  }];


  const CONTEXTUAL_COLORS_NOTES = CONTEXTUAL_COMMON_COLORS_NOTES;

  CONTEXTUAL_COLORS_NOTES.push({
    label: 'No Color',
    hexCode: '',
    data: {
      action: 'colorChange',
      hexCode: ''
    }
  });

  return {
    toggleTerms: true,
    udcCollectionId: null,
    showCanvasImages: true,
    showSerpAbstract: true,
    showSerpDescription: true,
    showSerpClaims: true,
    showSerpBrief: true,
    showSerpBackgroundText: true,
    showSerpImage: true,

    advfAllRate: 500,
    kwicView: false,
    shouldSync: true,
    serpPerPage: 10,
    serpHighlightSnippets: 2,
    serpHighlightSnippetsKey: 'tileViewDefaultSnippetsCount',
    serpSortParams: 'date_publ desc',
    nestedValueKeys: [],
    tileViewDefaultSnippetsCount: 2,
    tileViewSnippetsOptions: [2, 5, 10],
    tileViewNumResultsPerPage: 5,
    tileViewNumResultsPerInitialSearch: 10,
    gridViewNumResultsPerPage: 4,
    gridViewNumResultsPerInitialSearch: 8,
    PRE_LOAD_IMGS_CACHE_LIMIT_FOR_METRICS: 500,
    PRE_LOAD_IMGS_SPLICE_FROM_CACHE_FOR_METRICS: 100,
    SEARCH_RESULT_MEMORY_LIMIT: 20000,
    SEARCH_RESULT_CSV_EXPORT_LIMIT: 10000,
    defaultCaseName: 'Untitled Case',
    defaultSearchOperator: 'OR',
    searchResultsView: 'Grid',
    documentViewerView: 'Text',
    gadgets: ['searchHistorySettings', 'documentFilterSettings', 'searchResultSettings', 'helpPreferenceSettings', 'documentViewerSettings', 'taggedDocumentSettings'],
    userPreferenceElements: ['fontFamily', 'fontColor', 'backgroundColor', 'customTheme', 'fontSize', 'fontBold', 'hitTermUnderline'],
    highlightColors: ['#ff9999', '#ff9b99', '#ff9c99', '#ff9e99', '#ffa099', '#ffa299', '#ffa399', '#ffa599', '#ffa799', '#ffa899', '#ffaa99', '#ffac99', '#ffad99', '#ffaf99', '#ffb199', '#ffb399', '#ffb499', '#ffb699', '#ffb899', '#ffb999',
    '#ffbb99', '#ffbd99', '#ffbe99', '#ffc099', '#ffc299', '#ffc499', '#ffc599', '#ffc799', '#ffc999', '#ffca99', '#ffcc99', '#ffce99', '#ffcf99', '#ffd199', '#ffd399', '#ffd599', '#ffd699', '#ffd899', '#ffda99', '#ffdb99',
    '#ffdd99', '#ffdf99', '#ffe099', '#ffe299', '#ffe499', '#ffe699', '#ffe799', '#ffe999', '#ffeb99', '#ffec99', '#ffee99', '#fff099', '#fff199', '#fff399', '#fff599', '#fff799', '#fff899', '#fffa99', '#fffc99', '#fffd99',
    '#ffff99', '#fdff99', '#fcff99', '#faff99', '#f8ff99', '#f7ff99', '#f5ff99', '#f3ff99', '#f1ff99', '#f0ff99', '#eeff99', '#ecff99', '#ebff99', '#e9ff99', '#e7ff99', '#e6ff99', '#e4ff99', '#e2ff99', '#e0ff99', '#dfff99',
    '#ddff99', '#dbff99', '#daff99', '#d8ff99', '#d6ff99', '#d5ff99', '#d3ff99', '#d1ff99', '#cfff99', '#ceff99', '#ccff99', '#caff99', '#c9ff99', '#c7ff99', '#c5ff99', '#c3ff99', '#c2ff99', '#c0ff99', '#beff99', '#bdff99',
    '#bbff99', '#b9ff99', '#b8ff99', '#b6ff99', '#b4ff99', '#b3ff99', '#b1ff99', '#afff99', '#adff99', '#acff99', '#aaff99', '#a8ff99', '#a7ff99', '#a5ff99', '#a3ff99', '#a2ff99', '#a0ff99', '#9eff99', '#9cff99', '#9bff99',
    '#99ff99', '#99ff9b', '#99ff9c', '#99ff9e', '#99ffa0', '#99ffa2', '#99ffa3', '#99ffa5', '#99ffa7', '#99ffa8', '#99ffaa', '#99ffac', '#99ffad', '#99ffaf', '#99ffb1', '#99ffb3', '#99ffb4', '#99ffb6', '#99ffb8', '#99ffb9',
    '#99ffbb', '#99ffbd', '#99ffbe', '#99ffc0', '#99ffc2', '#99ffc4', '#99ffc5', '#99ffc7', '#99ffc9', '#99ffca', '#99ffcc', '#99ffce', '#99ffcf', '#99ffd1', '#99ffd3', '#99ffd5', '#99ffd6', '#99ffd8', '#99ffda', '#99ffdb',
    '#99ffdd', '#99ffdf', '#99ffe0', '#99ffe2', '#99ffe4', '#99ffe6', '#99ffe7', '#99ffe9', '#99ffeb', '#99ffec', '#99ffee', '#99fff0', '#99fff1', '#99fff3', '#99fff5', '#99fff7', '#99fff8', '#99fffa', '#99fffc', '#99fffd',
    '#99ffff', '#99fdff', '#99fcff', '#99faff', '#99f8ff', '#99f7ff', '#99f5ff', '#99f3ff', '#99f1ff', '#99f0ff', '#99eeff', '#99ecff', '#99ebff', '#99e9ff', '#99e7ff', '#99e6ff', '#99e4ff', '#99e2ff', '#99e0ff', '#99dfff',
    '#99ddff', '#99dbff', '#99daff', '#99d8ff', '#99d6ff', '#99d5ff', '#99d3ff', '#99d1ff', '#99cfff', '#99ceff', '#99ccff', '#99caff', '#99c9ff', '#99c7ff', '#99c5ff', '#99c3ff', '#99c2ff', '#99c0ff', '#99beff', '#99bdff',
    '#99bbff', '#99b9ff', '#99b8ff', '#99b6ff', '#99b4ff', '#99b3ff', '#99b1ff', '#99afff', '#99adff', '#99acff', '#99aaff', '#99a8ff', '#99a7ff', '#99a5ff', '#99a3ff', '#99a2ff', '#99a0ff', '#999eff', '#999cff', '#999bff',
    '#9999ff', '#9b99ff', '#9c99ff', '#9e99ff', '#a099ff', '#a299ff', '#a399ff', '#a599ff', '#a799ff', '#a899ff', '#aa99ff', '#ac99ff', '#ad99ff', '#af99ff', '#b199ff', '#b399ff', '#b499ff', '#b699ff', '#b899ff', '#b999ff',
    '#bb99ff', '#bd99ff', '#be99ff', '#c099ff', '#c299ff', '#c399ff', '#c599ff', '#c799ff', '#c999ff', '#ca99ff', '#cc99ff', '#ce99ff', '#cf99ff', '#d199ff', '#d399ff', '#d499ff', '#d699ff', '#d899ff', '#da99ff', '#db99ff',
    '#dd99ff', '#df99ff', '#e099ff', '#e299ff', '#e499ff', '#e699ff', '#e799ff', '#e999ff', '#eb99ff', '#ec99ff', '#ee99ff', '#f099ff', '#f199ff', '#f399ff', '#f599ff', '#f699ff', '#f899ff', '#fa99ff', '#fc99ff', '#fd99ff',
    '#ff99ff', '#ff99fd', '#ff99fc', '#ff99fa', '#ff99f8', '#ff99f7', '#ff99f5', '#ff99f3', '#ff99f1', '#ff99f0', '#ff99ee', '#ff99ec', '#ff99eb', '#ff99e9', '#ff99e7', '#ff99e5', '#ff99e4', '#ff99e2', '#ff99e0', '#ff99df',
    '#ff99dd', '#ff99db', '#ff99da', '#ff99d8', '#ff99d6', '#ff99d5', '#ff99d3', '#ff99d1', '#ff99cf', '#ff99ce', '#ff99cc', '#ff99ca', '#ff99c9', '#ff99c7', '#ff99c5', '#ff99c3', '#ff99c2', '#ff99c0', '#ff99be', '#ff99bd',
    '#ff99bb', '#ff99b9', '#ff99b8', '#ff99b6', '#ff99b4', '#ff99b3', '#ff99b1', '#ff99af', '#ff99ad', '#ff99ac', '#ff99aa', '#ff99a8', '#ff99a7', '#ff99a5', '#ff99a3', '#ff99a1', '#ff99a0', '#ff999e', '#ff999c', '#ff999b', '#ff9999'],

    customHighlightColors: [],

    systemFonts: [
    { label: 'Office Correspondence', value: ' ', disabled: true },
    { label: '  Arial', value: 'Arial' },
    { label: '  Times New Roman', value: 'Times New Roman' },
    { label: '', value: ' ', disabled: true },
    { label: 'All Fonts', value: '', disabled: true },
    { label: '  Agency FB', value: 'Agency FB' },
    { label: '  Arial Unicode MS', value: 'Arial Unicode MS' },
    { label: '  Calibri', value: 'Calibri' },
    { label: '  Century Schoolbook', value: 'Century Schoolbook' },
    { label: '  Georgia', value: 'Georgia' },
    { label: '  Batang', value: 'Batang' },
    { label: '  BatangChe', value: 'BatangChe' },
    { label: '  Century', value: 'Century' },
    { label: '  Bell MT', value: 'Bell MT' },
    { label: '  Book Antiqua', value: 'Book Antiqua' },
    { label: '  Bookman Old Style', value: 'Bookman Old Style' },
    { label: '  Californian FB', value: 'Californian FB' },
    { label: '  Calisto MT', value: 'Calisto MT' },
    { label: '  Cambria', value: 'Cambria' },
    { label: '  Cambria Math', value: 'Cambria Math' },
    { label: '  Candara', value: 'Candara' },
    { label: '  Consolas', value: 'Consolas' },
    { label: '  Constantia', value: 'Constantia' },
    { label: '  Corbel', value: 'Corbel' },
    { label: '  Courier New', value: 'Courier New' },
    { label: '  DokChampa', value: 'DokChampa' },
    { label: '  Dotum', value: 'Dotum' },
    { label: '  dotum che', value: 'dotum che' },
    { label: '  Ebrima', value: 'Ebrima' },
    { label: '  Estrangelo Edessa', value: 'Estrangelo Edessa' },
    { label: '  Footlight MT', value: 'Footlight MT' },
    { label: '  Franklin Gothic book', value: 'Franklin Gothic book' },
    { label: '  Garamond', value: 'Garamond' },
    { label: '  Gautami', value: 'Gautami' },
    { label: '  Gill Sans MT', value: 'Gill Sans MT' },
    { label: '  Goudy Old Style', value: 'Goudy Old Style' },
    { label: '  gulim', value: 'gulim' },
    { label: '  Helvetica', value: 'Helvetica' },
    { label: '  High Tower Text', value: 'High Tower Text' },
    { label: '  Lucida Console', value: 'Lucida Console' },
    { label: '  Lucida Bright', value: 'Lucida Bright' },
    { label: '  Lucida Fax', value: 'Lucida Fax' },
    { label: '  Lucida Sans', value: 'Lucida Sans' },
    { label: '  Lucida Sans Typewriter', value: 'Lucida Sans Typewriter' },
    { label: '  Lucida Sans Unicode', value: 'Lucida Sans Unicode' },
    { label: '  Malgun Gothic', value: 'Malgun Gothic' },
    { label: '  Mangal', value: 'Mangal' },
    { label: '  Microsoft Himalaya', value: 'Microsoft Himalaya' },
    { label: '  Modern No. 20', value: 'Modern No. 20' },
    { label: '  Mongolian Baiti', value: 'Mongolian Baiti' },
    { label: '  MS Gothic', value: 'MS Gothic' },
    { label: '  MS Mincho', value: 'MS Mincho' },
    { label: '  MS PMincho', value: 'MS PMincho' },
    { label: '  MS PGothic', value: 'MS PGothic' },
    { label: '  MS Reference Sans Serif', value: 'MS Reference Sans Serif' },
    { label: '  MS UI Gothic', value: 'MS UI Gothic' },
    { label: '  NSimSun', value: 'NSimSun' },
    { label: '  Palatino Linotype', value: 'Palatino Linotype' },
    { label: '  Perpetua', value: 'Perpetua' },
    { label: '  Plantagenet Cherokee', value: 'Plantagenet Cherokee' },
    { label: '  Poor Richard', value: 'Poor Richard' },
    { label: '  Raavi', value: 'Raavi' },
    { label: '  Rockwell', value: 'Rockwell' },
    { label: '  Shruti', value: 'Shruti' },
    { label: '  Simplified Arabic', value: 'Simplified Arabic' },
    { label: '  Simplified Arabic Fixed', value: 'Simplified Arabic Fixed' },
    { label: '  Sylfaen', value: 'Sylfaen' },
    { label: '  Tahoma', value: 'Tahoma' },
    { label: '  Trebuchet MS', value: 'Trebuchet MS' },
    { label: '  Tempo Grunge', value: 'Tempo Grunge' },
    { label: '  Tunga', value: 'Tunga' },
    { label: '  Tw Cen MT', value: 'Tw Cen MT' },
    { label: '  Vani ', value: 'Vani ' },
    { label: '  Verdana', value: 'Verdana' },
    { label: '  Vrinda', value: 'Vrinda' }],

    systemFontSizes: [
    { label: '8pt', value: '11px' },
    { label: '9pt', value: '12px' },
    { label: '10pt', value: '13px' },
    { label: '11pt', value: '15px' },
    { label: '12pt', value: '16px' },
    { label: '14pt', value: '19px' },
    { label: '16pt', value: '22px' },
    { label: '18pt', value: '24px' },
    { label: '20pt', value: '26px' },
    { label: '22pt', value: '29px' },
    { label: '24pt', value: '32px' },
    { label: '26pt', value: '35px' },
    { label: '28pt', value: '37px' },
    { label: '36pt', value: '48px' },
    { label: '48pt', value: '64px' }],

    famIdPreferredSourcesList: ['US-PGPUB', 'USPAT', 'FPRS'],
    appIdPreferredSourcesList: ['US-PGPUB', 'USPAT'],
    PRIORART: '1',
    INTERFERENCE: '2',
    USPAT: 'USPAT',
    US_PGPUB: 'US-PGPUB',
    USPGPUB: "USPGPUB",
    FPRS: 'FPRS',
    USOCR: 'USOCR',
    IBM_TDB: 'IBM_TDB',
    EPO: 'EPO',
    JPO: 'JPO',
    FIT: "FIT",
    DATABASES: ['USPAT', 'US-PGPUB', 'USOCR', 'FIT'],
    PGPUB_FULL: 'PGPubs Full',
    US_FULL: 'US Full Image',
    FO_FULL: 'Foreign Full Image',
    DEFAULT: 'Default',
    DERWENT: 'DERWENT',
    TAGGED_DOCUMENTS: 'taggedDocuments',
    SEARCH_RESULTS: 'searchResults',

    NOTES_VIEWER: 'notesViewer',
    DOCUMENT_VIEWER: "documentViewer",
    INDICES: '|did|icus|cxr|dw|ptpn|app|pckc|gofn|ds|apt|dd|apy|rrin|ddds|rlfd|pfpg|fd|pfpd|pfpc|rcco|ew|pfpa|sqor|pfpy|fmid|aaat|goeq|ddep|pfpn|asgp|fmio|lpar|rlcd|abdr|asc|ppsp|asn|inv|epcx|sqnr|fy|pix|fs|defn|art|sqoi|inzp|cccc|amud|emcd|ccco|fg|sqod|sqoc|rnsn|ipc|inzz|rlcy|npdw|epcs|ior|rnrx|rlcm|rlcn|epco|rlco|ctx|sqnb|gi|amrn|jftc|rfon|rnrl|abfn|isd|pfst|cloa|jfto|att|apcp|at|attn|as|ecxf|repn|aw|rcgp|ecxi|au|abeq|rfpn|ay|txt|ipfc|ecxs|rfpd|ad|asci|adoi|repd|ab|adod|atty|asco|ai|ascc|adoc|py|ap|ecxp|an|pmc|rlgk|tdid|bi|lrnm|pdid|fipc|aaco|rlhd|apan|dc|rfrs|apac|aaci|ple|fscp|rlgm|nran|fscs|rlgy|dwku|pfrt|fscl|codr|rfkc|icls|aspc|mc|fabs|inst|nfg|prcu|pctl|cocn|lrag|patn|rckd|clas|ttai|intx|prcc|prco|patt|pctx|cicl|abme|ctac|pan|nrdw|nrdt|nr|pac|ilrd|rin|ilrn|rlkd|rlkc|bspr|ccls|apdw|unit|lrci|xnpl|dcfn|amks|pray|rpkd|insa|rfnp|pn|rfnm|pi|prad|cidx|cmcd|lan|pk|pd|cuas|prai|pg|pran|lrco|pa|lrcn|rfnr|aagp|pc|ctcp|rcpn|rlpy|chem|ctco|dceq|docn|rcpd|dreq|clfn|sqtx|pgpd|ilpd|lrea|cpcc|tbcp|cifc|ddan|aanm|gau|in|sqtl|pcpd|ciff|cpca|deeq|cleq|ncl|pcpk|pcpm|pcpn|rpps|cpct|icpg|pcps|pcpt|rlrp|pcpx|cpcl|cpcg|sqtb|cpci|dcc|ndr|rppc|pfyy|asnp|sitx|asnm|bstl|rep|bstx|rfip|dcx|rfig|ref|kd|ecl|drfn|reex|tban|rlpd|rlpc|ptpd|ks|abpn|bsum|la|rlpm|pazz|rlpk|refd|rpnr|pgpy|invt|pct|rlpp|rlpn|pgkc|fss|ccsr|ptad|ptac|jfac|lrzc|rfco|ppcc|ptan|dbnm|bvrf|ran|fpar|jfao|rac|recd|gotl|fsc|gotx|epi|appl|cixr|tt|fsi|xp|tbti|prir|acc|blnm|rltc|san|xa|abtl|tbtx|rcsp|ciux|tix|rean|tbse|apnr|inir|read|inif|abtx|aszp|rctx|aszz|abb|nps|pgnr|frgp|prhy|dnc|abe|prid|size|crtx|afd|rc|isy|assa|tbvl|aisd|urnm|ciso|parn|pfde|pfdd|pfdc|cisr|dclm|pfdm|asst|pfdk|fref|jpft|sec|ranc|rpgp|piph|astc|cpli|astx|jpfi|cpla|ranr|btnc|py|inni|bic|pfap|innm|ti|tbxr|aast|pfay|afft|drno|chnl|urpn|rpid|drnr|agt|ilfd|urpd|ccpr|afff|papc|chmy|cofc|chmx|cpoa|nrpn|chmz|ptfd|frcc|cisi|aatt|so|rfad|aatx|frco|frcp|bis|vol|ccor|innc|ixr|chmt|pfad|chmu|frcl|chmv|chmw|ipxe|cior|aazp|cpog|pgcd|gpd|cpoi|jfic|ttl|cipc|frpd|cipg|bgtx|drn|ttx|indc|frpn|cloi|ipct|cips|cipr|ipcx|fmbi|fmbg|incr|dupk|depr|ipcm|incs|firm|ipcn|cor|ipco|ipcp|cipp|inco|ipcr|cipn|ipcs|cpi|ipce|pcco|ppkc|ipcg|ipcf|dipw|ipci|ipch|botn|inci|cpa|incc|cpc|pgco|ipca|jfio|ipcc|prrd|trc|prrn|trm|lrst|src|clm|pcfn|ctri|trx|pcdw|pcdv|pceq|pfdw|pfdt|pfds|inaa|lrsa|fror|corr|pfdn|fpd|prx|drtx|pt1d|pry|clta|tbnr|dctx|prpc|pflt|clsp|prd|drtl|prc|pppd|dnn|pfla|prn|clss|fsic|clst|oref|ppnr|gopr|detx|ptc|lrtx|nrwk|wku|cltl|cltx|ingp|bsfn|supb|pcan|sdrc|dsrc|sdrf|pt3d|rlan|r47x|tbpy|drwd|pub|apg|apn|nryy|urcp|detd|tbpg|urcl|urgp|tbpb|detl|apd|bseq|tbpd|uref|msgr|bgtl|rlac|rlad|fpy|ccxr|rpak|pcad|rpan|pcac|cond|dctl|rpac|pcam|rpaf|pcak|cied|clms|orpl|exp|lrfw|arp|aad|abpr|apsn|ard|cc|cfsi|cfss|cifs|clpr|cpcx|dcd|dcpr|dkwu|drpr|gisd|govh|lid|lrfm|pcfd|ptab|spec|urux|xnpr|xpa|aars|aant|ase|asne|ine|inve|urxr|',
    SPECIAL_INDICES: '|sub|sub|ang|deg|degree|sup|',
    RANGE_INDICES: '|@ad|@ap|@apnr|@src|@ay|@dd|@size|@art|@frpd|@gpd|@ncl|@ndr|@nfg|@pfdd|@pt3d|@ptad|@ptpd|@py|@pppd|@pray|@prad|@pd|@pn|@rlhd|@rlfd|@rlpd|@trm|@urpd|@fd|@afd|@prrd|@pcdv|@tbpy|@apd|@rlad|@fpy|@pcad|@aisd|@ilfd|@ilpd|@ilrd|@isd|@isy|@prhy|@prpc|@ptfd|@read|@dcd|@gisd|@pcdw|@pt1d|@repd|@rpid|@refd|@rpaf|@pgpd|@pgpy|@rfpd|@pfad|@nryy|@nrdt|@prd|@pfpd|@pfdt|@rcpd|@fpd|@tbpd|@docn|',
    ALLOWED_MAX_DOC_SIZE_TO_DISPLAY: 2621440,
    DOUABLE_CLICK_DELAY: 300,
    SEARCH_PRIOR_ART: 1,
    SEARCH_TYPE_BROWSE: 'browse',
    SEARCH_TYPE_PN: 'pn',
    SEARCH_TYPE_LIST: 'list',
    SEARCH_TYPE_REFRESH: 'refresh',
    SEARCH_TYPE_SEARCH: 'search',
    SEARCH_TYPE_SEARCH_HISTORY: 'listH',
    EXTERNAL_QUERY_TYPE_IDS: 'ids',
    EXTERNAL_QUERY_TYPE_QUERYSTRING: 'queryString',

    DERWENT_FIT_COPYRIGHT_TXT_PART1: '<i>Copyright &copy;',
    DERWENT_FIT_COPYRIGHT_TXT_PART2: ' Clarivate Analytics. All rights reserved. Republication or redistribution of Clarivate Analytics content, including by framing or similar means, is prohibited without the prior written consent of Clarivate Analytics. Clarivate and its logo are trademarks of the Clarivate Analytics group.</i>',

    //preferences keys
    PREFERENCE_SEARCH_RESULTS_KEY: 'PREFERENCE-searchResults-data',
    PREFERENCE_DOCUMENT_VIEWER_KEY: 'PREFERENCE-documentViewer-data',
    PREFERENCE_SEARCH_HISTORY_KEY: 'PREFERENCE-searchHistory-data',
    PREFERENCE_NOTES_VIEWER_KEY: 'PREFERENCE-notesViewer-data',
    PREFERENCE_HELP_KEY: 'PREFERENCE-help-data',
    PREFERENCE_TAGGED_DOCS_KEY: 'PREFERENCE-taggedDocument-data',
    PREFERENCE_COLLECTIONS_KEY: 'PREFERENCE-collections-data',
    PREFERENCE_DEFAULT_WORKSPACE_LAYOUT_KEY: 'PREFERENCE-workspaceLayout-default',
    PREFERENCE_USER_PREFERENCES_KEY: 'PREFERENCE-userPreferences-data',
    PREFERENCE_DEFAULT_BROWSER_LAYOUT_KEY: 'PREFERENCE-browserLayout-default',
    PREFERENCE_DEFAULT_WORKSPACE_KEY: 'PREFERENCE-workSpace-default',
    PREFERENCE_DOCUMENT_FILTERS_KEY: 'PREFERENCE-documentFilters-data',
    PREFERENCE_HIT_TERMS_KEY: 'PREFERENCE-hitTerms-data',

    SEARCH_PREFETCH_PAGE_SIZE: 100,
    SEARCH_PREFETCH_PAGE_SIZE_LIMIT: 100,
    CUSTOM_SORT_PAGE_SIZE: 10000,

    SHOWRESULTS_YES: '1',
    SHOWRESULTS_NO: '0',
    SHOWRESULTS_LIMIT: '2',
    notesOpen: 1,
    notesClose: 0,
    notesVisible: 0,
    notesInvisible: 1,

    //notes tags
    NOTE_TAG_LABEL_101: '101',
    NOTE_TAG_LABEL_102: '102',
    NOTE_TAG_LABEL_103: '103',
    NOTE_TAG_LABEL_112: '112',
    NOTE_TAG_LABEL_RA: 'Reason for Allowance',
    NOTE_TAG_LABEL_MISC: 'Miscellaneous',
    NOTE_TAG_LABEL_DP: 'Double Patenting',
    NOTE_TAG_LABEL_OT: 'userDefinedTagLabel',
    NOTE_TAG_DP_ID: 'doublePatenting',
    NOTE_TAG_RA_ID: 'reasonForAllowance',
    NOTE_TAG_MISC_ID: 'miscellaneous',
    NOTE_TAG_OT_ID: 'userDefinedTagChk',
    NOTE_TAG_LABEL_UDT: 'OT',
    NOTE_TAG_LABEL_RA_ABBR: 'RA',
    NOTE_TAG_LABEL_MISC_ABBR: 'MISC',
    NOTE_TAG_LABEL_DP_ABBR: 'DP',

    //notes panel more/less char limit
    NOTES_PANEL_CARD_CHAR_LIMIT: 300,
    NOTE_TYPE_IMAGE: 'Image',
    NOTE_TYPE_TEXT: 'Text',
    NOTE_TEXT_CHAR_LIMIT_FOR_OVERLAY: 200,
    //PRINT IMAGE CONSTANTS
    PRINT_DOC_CSS: '@media print { @page { size: 8.51in 11in; margin: 0mm 0mm 0mm 0mm;}html {  background-color: #FFFFFF;  margin: 0px; }body {  margin: 0mm 5mm 0mm 0mm;} .pagebreak { page-break-before: always; } }',
    PRINT_DOC_STYLE: '<style>@media print { @page { size: 8.51in 11in; margin: 0mm 0mm 0mm 0mm;}html {  background-color: #FFFFFF;  margin: 0px; }body {  margin: 0mm 5mm 0mm 0mm;} .pagebreak { page-break-before: always; } }</style>',
    PRINT_DOC_IMAGE_HEIGHT: '1168',
    PRINT_DOC_IMAGE_WIDTH: '920',

    //PRINT TEXT AND TEXT+IMAGE CONSTANTS
    PRINT_DOC_TEXT_CSS: '@media print { .document_heading, .documentText, .labelText { color: #000000!important; } @page { margin: 4mm 10mm 4mm;} .pagebreak { page-break-before: always; } }',
    PRINT_DOC_TEXT_STYLE: '<style>@media print { @page {  margin: 4mm 0mm 4mm 0mm;}html { color: #000000; background-color: #FFFFFF;  margin: 0px; }body {  margin: 0mm 5mm 0mm 0mm;} .pagebreak { page-break-before: always; } }</style>',
    PRINT_DOC_TEXT_IMAGE_HEIGHT: '1130',

    //PRINT NOTE CONSTANTS
    //CSS footer holder incase needed later: #content { display:table; } #pagefooter { display: table-footer-group; position:fixed; bottom: 0; } #pagefooter:after{counter-increment: page; content: 'Page ' counter(page);}
    NOTE_PRINT_DOC_STYLE: '',
    NOTE_PRINT_DOC_STYLE_HIDE_TOP: '<style>@media print {  @page { size: 8.51in 11in; margin: 10px 10px 50px 10px; }</style>',

    NOTE_ACTION_TYPE_ADD: 'add',
    NOTE_ACTION_TYPE_DELETE: 'delete',
    NOTE_ACTION_TYPE_UPDATE: 'update',
    NOTE_COLOR_MAP: {
      '#ff6666': 'Red',
      '#ffcc66': 'Orange',
      '#ffff33': 'Yellow',
      '#33ff33': 'Green',
      '#66ccff': 'Blue',
      '#00ffff': 'Cyan',
      '#ccccff': 'Lavendar',
      '#cc66ff': 'Purple'
    },
    SECTIONS_MUTISELECT_PLACEHOLDER: 'Select sections',
    TEXT_VIEWER_METADATA_FIELDS: ['meta-inventionTitle',
    'meta-publicationReferenceDocumentNumber',
    'meta-guid',
    'meta-datePublished',
    'meta-source',
    'meta-patentFamilyId',
    'meta-priorPublInfoGroup',
    'meta-inventorsInfoGroup',
    'meta-applicantInfoGroup',
    'meta-assigneeInfoGroup',
    'meta-applicationNumber',
    'meta-applicationFilingDate',
    'meta-priorityClaimsDateGroup',
    'meta-relatedApplFilingDateGroup',
    'meta-pctData',
    'meta-hagueData',
    'meta-usClassCurrent',
    'meta-usClassIssued',
    'meta-cpcIssuedGroup',
    'meta-cpcCurrentGroup',
    'meta-intlClassIssuedGroup',
    'meta-intlClassCurrentGroup',
    'meta-usReferences',
    'meta-foreignReferences',
    'meta-otherPublications',
    'meta-artUnit',
    'meta-primaryExaminer',
    'meta-assistantExaminer',
    'meta-agent',
    'meta-fieldOfClassSearch',
    'meta-derwentInfoGroup',
    'meta-cpcCombinationSetsGroup',
    'meta-correspondenceAddress',
    'meta-usRefIssuedDate',
    'meta-kwicHits'],

    TEXT_VIEWER_SECTIONS: ['abstractNode',
    'equivalentAbstractNode',
    'chemicalCodesNode',
    'governmentInterestNode',
    'briefNode',
    'descriptionNode',
    'claimsNode',
    'sequenceListingNode'],

    HIDEABLE_GADGET_SCRIPT: ['searchResults', 'search'],
    HIDEABLE_GADGET_SCRIPT_BROWSER: ['searchResults'],

    SEARCHRESULTS_SCRIPT: 'searchResults',
    SEARCHRESULTS_SHORT: 'SR',
    TAGGEDDOCUMENTS_SHORT: 'TD',

    REFRESH_ALL_LIMIT: 5000,
    SEARCH_HISTORY_GRID_RENDER_COUNT_FOR_REFRESH: 100,
    REFRESH_ALL_ACTION_COMPLETE: 'complete',
    REFRESH_ALL_ACTION_CANCELED: 'canceled',
    REFRESH_ALL_STATUS_COMPLETED: 'COMPLETED',
    REFRESH_ALL_STATUS_CANCELED: 'CANCELED',
    REFRESH_ALL_STATUS_PARTIAL: 'PARTIAL-REFRESH',
    REFRESH_ALL_STATUS_STARTED: 'STARTED',
    REFRESH_ALL_STATUS_FAILED: 'FAILED',
    SEARCH_HISTORY_SEARCH_TYPE_PRIOR_ART: 'Prior Art',
    SEARCH_HISTORY_SEARCH_TYPE_INTERFERENCE: 'Interference',
    DOC_FILTERS_PANEL_STATE_CLOSE: 'closed',
    sortStr: 'score%20desc',
    SORT_DESC_UPPER: 'DESC',

    FONT_SIZE_8pt: '11px',
    FONT_SIZE_9pt: '12px',
    FONT_SIZE_10pt: '13px',
    FONT_SIZE_11pt: '15px',
    FONT_SIZE_12pt: '16px',
    FONT_SIZE_14pt: '19px',
    FONT_SIZE_16pt: '22px',
    FONT_SIZE_18pt: '24px',
    FONT_SIZE_20pt: '26px',
    FONT_SIZE_22pt: '29px',
    FONT_SIZE_24pt: '32px',
    FONT_SIZE_26pt: '35px',
    FONT_SIZE_28pt: '37px',
    FONT_SIZE_36pt: '48px',
    FONT_SIZE_48pt: '64px',

    MESSAGE_SRM_FIRST_DOC: 'MESSAGE-SRM-firstDoc',
    MESSAGE_SRM_LAST_DOC: 'MESSAGE-SRM-lastDoc',
    MESSAGE_SRM_NEXT_DOC: 'MESSAGE-SRM-nextDoc',
    MESSAGE_SRM_PREVIOUS_DOC: 'MESSAGE-SRM-previousDoc',

    PATENT_IMAGE_NOT_FOUND: 'images/imagenotfound.png',
    PATENT_IMAGE_WITHDRAWN: 'images/patentwithdrawn.png',
    PATENT_IMAGE_DELETED: 'images/patentdeleted.png',
    PATENT_IMAGE_NOT_AVAILABLE: 'images/noImageYet.png',
    PATENT_IMAGE_SECTION_NOT_AVAILABLE: 'images/sectionnotavailable.png',
    PATENT_IMAGE_SERVER_ERROR: 'images/serverImg.png',

    PAGE_ERROR: 'errorPage.html',
    PAGE_NO_ACCESS: 'noAccessPage.html',


    SCROLL_BAR_WIDTH: 22,
    TOTAL_DB_NUM_TYPE1: 3,


    IMAGE_SECTION_FULL: 'full',

    NOTIFICATIONS_TIMEOUT: 25000,
    NOTIFICATIONS_TYPE_ERROR: 'error',
    NOTIFICATIONS_TYPE_INFO: 'info',
    API_USER_TIMEOUT: 7000,
    API_TIMEOUT: 15000,
    API_TIMEOUT_30_SECS: 30000,
    API_TIMEOUT_1_MIN: 60000,

    CAT_LINK_LOCAL: 'http://cpc1.dev.uspto.gov/mcc/secure/index.html#/home',
    CAT_LINK_SIT: 'http://cpc1.dev.uspto.gov/mcc/secure/index.html#/home',
    CAT_LINK_FQT: 'http://cpc1.dev.uspto.gov/mcc/secure/index.html#/home',
    CAT_LINK_PVT: 'http://cpc1.dev.uspto.gov/mcc/secure/index.html#/home',
    CAT_LINK_PROD: 'http://cpc.uspto.gov/mcc/secure/index.html#/home',
    CLASSIFICATION_HOME_PAGE: 'http://ptoweb.uspto.gov/patents/classification-resources/',
    GLOBAL_DOSSIER: 'https://globaldossier.uspto.gov/#/',
    STIC: 'https://usptogov.sharepoint.com/sites/09cdab00/',
    PALM_ART_SEARCH: 'http://es/emlocator/qryTCTransferSearch.do',
    DAV_LINK_LOCAL: 'https://dav.local.uspto.gov/webapp/login.html',
    DAV_LINK_SIT: 'https://dav.sit.uspto.gov/webapp/login.html',
    DAV_LINK_FQT: 'https://dav.fqt.uspto.gov/webapp/login.html',
    DAV_LINK_PVT: 'https://dav.pvt.uspto.gov/webapp/login.html',
    DAV_LINK_PROD: 'https://dav.uspto.gov/webapp/',
    OC_LINK_LOCAL: 'https://dav.local.uspto.gov/oc/login.html',
    OC_LINK_SIT: 'https://dav.sit.uspto.gov/oc/login.html',
    OC_LINK_FQT: 'https://dav.fqt.uspto.gov/oc/login.html',
    OC_LINK_PVT: 'https://dav.pvt.uspto.gov/oc/login.html',
    OC_LINK_PROD: 'https://dav.uspto.gov/oc/',
    MAX_IMAGE_REDRAW_ATTEMPTS: 3,
    MAX_IMAGES_FOR_FRONT_END_PRINT: 250,
    MAX_DOC_SIZE_FOR_FRONT_END_PRINT: 468347,
    EST_BROWSER_NAME: 'estbrowser',
    WEST_BROWSER_NAME: 'westSideBySide',
    MAX_RESULTS_FOR_SEARCH_ALL: 10000,
    ON_DEMAND: 'ondemand',
    MANUAL: 'manual',
    EST_MAIN_WINDOW_NAME: 'estconsole',

    DATE_PUBL_ON: '=',
    DATE_PUBL_BEFORE: '<=',
    DATE_PUBL_AFTER: '>=',


    BIG_MONTH: ['01', '03', '05', '07', '08', '10', '12'],
    SMALL_MONTH: ['04', '06', '09', '11'],

    TD_TIMEOUT_DELAY: 100,

    SEARCH_BRS_PROXIMITY_LIMITS: {
      'SAME': 25,
      'WITH': 25,
      'ADJ': 450,
      'NEAR': 450
    },

    //The following 2 are added SOLELY to trick es5 to compiling the valid regex that it thinks is invalid
    SEARCH_LOOKBEHIND_IGNORE_SPECIAL_CHARS: '(?<=\\s|\\(|\\)|>|<|&nbsp;|^)',
    SEARCH_LOOKAHEAD_IGNORE_SPECIAL_CHARS: '(?=\\s|\\(|\\)|>|<|&nbsp;|$)',
    LOOKBEHIND_SPACE_PARENTHESIS: '(?<=\\s|\\()',
    //gadget names
    SEARCH_HISTORY_GADGET: 'searchHistory',

    HITTERMS_LOADER_THRESHOLD: 2500,

    VPAGE_CACHED: '(cached)',

    OVERLAY_FADE_TIME_MS: 200,

    // modal size classes
    MODAL_SIZE_S: 'modal-sm',
    MODAL_SIZE_M: 'modal-md',
    MODAL_SIZE_L: 'modal-lg',

    docNavGroups: { "docNavAll": 1, "docNavPrevNext": 2, "docNavFirstLast": 3 },
    pageNavGroups: { "pageNavAll": 1, "pageNavPrevNext": 2, "pageNavFirstLast": 3 },
    docNavButtons: { firstDoc: "firstDocument", previousDoc: "prevDocument", nextDoc: "nextDocument", lastDoc: "lastDocument" },
    pageNavButtons: { firstPageNum: "firstPage", prevPageNum: "prevPage", nextPageNum: "nextPage", lastPageNum: "lastPage" },
    IMAGES: 'Images',
    TEXT: 'Text',

    // Where a query originated, such as an examiner drafting it or an AI tool
    QUERY_SOURCE: {
      BRS: 'brs',
      MLTD: 'mltd',
      SIMILARITY: 'similarity'
    },

    multiSelectViews: { Images: 'imageView', Text: 'textView' },

    TOOLBAR_KEY_ICON_MAP: {
      // common icons
      widgetToolbarScrollUp: 'icon-arrow-up button-secondary',
      widgetToolbarScrollDown: 'icon-arrow-down button-secondary',
      preferences: 'icon-cogs',
      ered: 'icon-folder',
      firstDocument: 'icon-fast-backward',
      prevDocument: 'icon-backward',
      documentNumber: 'icon-document has-dynamic-tooltip',
      nextDocument: 'icon-forward',
      lastDocument: 'icon-fast-forward',
      backwardCitation: 'icon-quote-left',
      backwardForwardCitation: 'icon-quote',
      forwardCitation: 'icon-quote-right',
      moreLikeThisDoc: 'icon-more-like-doc',
      imgBackwardCitation: 'icon-quote-left',
      imgBackwardForwardCitation: 'icon-quote',
      imgForwardCitation: 'icon-quote-right',

      // Text viewer icons
      switchToImage: 'icon-image',
      textPrint: 'icon-print',
      kwic: 'icon-k',
      metadata: 'icon-triangle',
      findWithin: 'icon-search',
      advancedFind: 'icon-zoom',
      docSections: 'icon-section',
      highlights: 'icon-highlights',
      prevKeyword: 'icon-key-up',
      nextKeyword: 'icon-key-down',

      // image viewer icons
      switchToText: 'icon-text',
      imagePrint: 'icon-print',
      save: 'icon-save',
      fitToWidth: 'icon-arrows-h',
      fitToWindow: 'icon-expand-arrows',
      invertColor: 'icon-adjust',
      imageZoom: 'icon-percent has-dynamic-tooltip',
      imgSections: 'icon-section has-dynamic-tooltip',
      rotateLeft: 'icon-rotate-left',
      rotateRight: 'icon-rotate-right',
      toggleNotesPanel: 'icon-sticky-note',
      firstPage: 'icon-step-backward',
      prevPage: 'icon-caret-left',
      pageNumber: 'icon-page has-dynamic-tooltip',
      nextPage: 'icon-caret-right',
      lastPage: 'icon-step-forward'

    },

    FORWARD_CITATION_SEARCH: "Forward citation search",
    BACKWARD_CITATION_SEARCH: "Backward citation search",
    COMBINED_CITATION_SEARCH: "Combined citation search",

    MENU_FORWARD_CITATION_SEARCH_LBL: "Forward",
    MENU_BACKWARD_CITATION_SEARCH_LBL: "Backward",
    MENU_COMBINED_CITATION_SEARCH_LBL: "Simultaneous backward and forward",

    /* Contextual color options */
    CONTEXTUAL_COLORS_TAGS: [{
      label: 'Green',
      hexCode: '#89D568',
      data: {
        action: 'colorChange',
        hexCode: '#89D568'
      }
    },
    {
      label: 'Blue',
      hexCode: '#5EACF3',
      data: {
        action: 'colorChange',
        hexCode: '#5EACF3'
      }
    },
    {
      label: 'Orange',
      hexCode: '#FF9C34',
      data: {
        action: 'colorChange',
        hexCode: '#FF9C34'
      }
    },
    {
      label: 'Deep blush',
      hexCode: '#DD6CA7',
      data: {
        action: 'colorChange',
        hexCode: '#DD6CA7'
      }
    },
    {
      label: 'Purple',
      hexCode: '#836DC4',
      data: {
        action: 'colorChange',
        hexCode: '#836DC4'
      }
    },
    {
      label: 'Indigo',
      hexCode: '#4F77CA',
      data: {
        action: 'colorChange',
        hexCode: '#4F77CA'
      }
    },
    {
      label: 'Red',
      hexCode: '#FC3636',
      data: {
        action: 'colorChange',
        hexCode: '#FC3636'
      }
    }],


    CONTEXTUAL_COLORS_HIGHLIGHT: CONTEXTUAL_COMMON_COLORS_NOTES,

    CONTEXTUAL_COLORS_NOTES: CONTEXTUAL_COLORS_NOTES,
    PCT_APPLICATION_TEXT: 'PCT',
    NON_SQM_ERROR_TEXT: 'Unable to process your request, please try again later.',
    APPLICATION_ERROR_TEXT: 'Application Number is invalid',
    HYPERLINK_BULKDATA_REGEX: new RegExp('(https:\\/\\/bulkdata\\.uspto\\.gov\\/data2\\/lengthysequencelisting\\/\\d{4}\\/)', 'g'),
    HYPERLINK_BULKDATA_REPLACE_TEXT: '<a class="application_link" href="$1" target="_blank">$1</a>)',
    HYPERLINK_SEQDATA_BULKDATA_REGEX: new RegExp("(http:\\/\\/seqdata\\.uspto\\.gov.*?)(\\))|(https:\\/\\/seqdata\\.uspto\\.gov.*?)(\\))|(https:\\/\\/bulkdata\\.uspto\\.gov\\/data2\\/lengthysequencelisting\\/\\d{4}\\/)", "g"),
    HYPERLINK_SEQDATA_BULKDATA_REPLACE_TEXT: '<a class="application_link" href="$1$3" target="_blank">$1$3</a>$2',

    FILE_MAX_SIZE: 10000000, // 10MB
    FILE_MIN_SIZE: 100, //100KB,

    FEATURES: [{
      title: 'Search History - Draft Queries',
      name: 'featureDraftFolders',
      files: [
      'gadgets/search/search',
      'gadgets/searchHistory/searchHistory',
      'gadgets/searchResults/searchResults']

    },
    {
      title: 'WEST Search Results',
      name: 'featureWestSearchResults',
      files: [
      // We added CSS in the below source in order for the application to avoid
      // looking for the extended search.js file since there are none
      // We are using this to add a class to the gadget
      'CSS!gadgets/searchResults/searchResults']

    },
    {
      title: 'More Like This document',
      name: 'featureMoreLikeThisDocument',
      files: [
      // We added CSS in the below source in order for the application to avoid
      // looking for the extended search.js file since there are none
      // We are using this to add a class to the gadget
      'CSS!gadgets/searchResults/searchResults']

    },
    {
      title: 'A-Z Keyboard Tagging Preference',
      name: 'featureAZTaggingPreference',
      files: [
      // We added CSS in the below source in order for the application to avoid
      // looking for the extended search.js file since there are none
      // We are using this to add a class to the gadget
      'CSS!gadgets/searchResults/searchResults']

    }],


    FIT_COUNTRIES: [
    {
      label: 'North America',
      columnDividerStartIndex: [0, 1, 2],
      columnDividerEndIndex: [0, 1, 2],
      countries: [
      {
        label: 'Canada',
        id: 'CA'
      },
      {
        label: 'Cuba',
        id: 'CU'
      },
      {
        label: 'Mexico',
        id: 'MX'
      }]

    },
    {
      label: 'Europe',
      columnDividerStartIndex: [0, 11, 22, 33],
      columnDividerEndIndex: [10, 21, 32, 41],
      countries: [
      {
        label: 'Austria',
        id: 'AT'
      },
      {
        label: 'Belarus',
        id: 'BY'
      },
      {
        label: 'Belgium',
        id: 'BE'
      },
      {
        label: 'Bulgaria',
        id: 'BG'
      },
      {
        label: 'Croatia',
        id: 'HR'
      },
      {
        label: 'Czech',
        id: 'CS'
      },
      {
        label: 'Czech Republic',
        id: 'CZ'
      },
      {
        label: 'Denmark',
        id: 'DK'
      },
      {
        label: 'Estonia',
        id: 'EE'
      },
      {
        label: 'Eurasian',
        id: 'EA'
      },
      {
        label: 'European Patent Office',
        id: 'EPO'
      },
      {
        label: 'Finland',
        id: 'FI'
      },
      {
        label: 'France',
        id: 'FR'
      },
      {
        label: 'Germany',
        id: 'DEC'
      },
      {
        label: 'Germany-East',
        id: 'DD'
      },
      {
        label: 'Hungary',
        id: 'HU'
      },
      {
        label: 'Iceland',
        id: 'IS'
      },
      {
        label: 'Ireland',
        id: 'IE'
      },
      {
        label: 'Israel',
        id: 'IL'
      },
      {
        label: 'Italy',
        id: 'IT'
      },
      {
        label: 'Latvia',
        id: 'LV'
      },
      {
        label: 'Lithuania',
        id: 'LT'
      },
      {
        label: 'Luxembourg',
        id: 'LU'
      },
      {
        label: 'Moldova',
        id: 'MD'
      },
      {
        label: 'Monaco',
        id: 'MC'
      },
      {
        label: 'Netherlands',
        id: 'NL'
      },
      {
        label: 'Norway',
        id: 'NO'
      },
      {
        label: 'Poland',
        id: 'PL'
      },
      {
        label: 'Portugal',
        id: 'PT'
      },
      {
        label: 'Romania',
        id: 'RO'
      },
      {
        label: 'Russian Federation',
        id: 'RU'
      },
      {
        label: 'Serbia',
        id: 'RS'
      },
      {
        label: 'Slovakia',
        id: 'SK'
      },
      {
        label: 'Slovenia',
        id: 'SI'
      },
      {
        label: 'Soviet Union',
        id: 'SU'
      },
      {
        label: 'Spain',
        id: 'ES'
      },
      {
        label: 'Sweden',
        id: 'SE'
      },
      {
        label: 'Switzerland',
        id: 'CH'
      },
      {
        label: 'Turkey',
        id: 'TR'
      },
      {
        label: 'Ukraine',
        id: 'UA'
      },
      {
        label: 'United Kingdom',
        id: 'GB'
      }]

    },
    {
      label: 'Asia',
      columnDividerStartIndex: [0, 3, 6, 9],
      columnDividerEndIndex: [2, 5, 8, 11],
      countries: [
      {
        label: 'China',
        id: 'CN'
      },
      {
        label: 'India',
        id: 'IN'
      },
      {
        label: 'Indonesia',
        id: 'ID'
      },
      {
        label: 'Japan',
        id: 'JP'
      },
      {
        label: 'Korea',
        id: 'KR'
      },
      {
        label: 'Malaysia',
        id: 'MY'
      },
      {
        label: 'Mongolia',
        id: 'MN'
      },
      {
        label: 'Philippines',
        id: 'PH'
      },
      {
        label: 'Singapore',
        id: 'SG'
      },
      {
        label: 'Taiwan',
        id: 'TW'
      },
      {
        label: 'Thailand',
        id: 'TH'
      },
      {
        label: 'Vietnam',
        id: 'VN'
      }]

    },
    {
      label: 'Other',
      columnDividerStartIndex: [0, 2, 4, 6],
      columnDividerEndIndex: [1, 3, 5, 7],
      countries: [
      {
        label: 'African Regional IPO',
        id: 'AP'
      },
      {
        label: 'African IPO',
        id: 'OAPI'
      },
      {
        label: 'Australia',
        id: 'AU'
      },
      {
        label: 'Brazil',
        id: 'BR'
      },
      {
        label: 'Morocco',
        id: 'MA'
      },
      {
        label: 'New Zealand',
        id: 'NZ'
      },
      {
        label: 'Tunisia',
        id: 'TN'
      },
      {
        label: 'WIPO',
        id: 'WO'
      }]

    }],


    DRAFT_GROUP_ID: 0,
    TRASH_GROUP_ID: 15,
    PRIOR_ART_GROUP_ID: 5,
    INTERFERENCE_GROUP_ID: 10,
    SEARCH_TERM_TYPES: ['TERM', 'WILDCARD_TERM', 'SLART_TERM'],
    WILDCARD_SLART_TERMS: ['WILDCARD_TERM', 'SLART_TERM'],
    WILDCARD_TERM: 'WILDCARD_TERM',
    SLART_TERM: 'SLART_TERM',

    // Citation Search Overlay
    CITATION_SEARCH_OVERLAY_DOC_LIMIT: 100,
    CITATION_SEARCH_OVERLAY_TITLE: 'Backward and Forward Citations Search',
    CITATION_SEARCH_OVERLAY_CONTENT_PATH: 'features/citationSearchOverlay/citationSearchOverlay',
    CITATION_SEARCH_OVERLAY_ATTR: 'citationSearchOverlayForTdAndSR',
    CITATION_SEARCH_OVERLAY_SELECTION_MSG: 'A maximum of 100 U.S. documents are considered in each citation search request. ' +
    'Citation searches can only be performed on references from the USPAT, US-PGPUB, and USOCR databases and exclude foreign documents.',

    ADVANCED_SESSION_KEY: 'advanced_lastUsedSessionId',
    ACCESS_TOKEN_KEY: 'x-access-token',

    SELECTED_FIT_COUNTRIES: 'selected_fit_countries',

    // Prompt Overlay
    PROMPTOVERLAY_CLASSNAME: 'promptForActionOverlay',
    PROMPTOVERLAY_CONTENT_PATH: 'widgets/imageViewer/promptForAction',
    PROMPTOVERLAY_EOC_TITLE: 'End of Collection',
    PROMPTOVERLAY_PFA_TITLE: 'Prompt for Action',

    // PSAI Config
    PSAI_MLTD: '../api/ppubs-ai/doceng/doc-expand',
    PSAI_ANALYTICS_V2: '../ppubs-ai/analytics/v2/metrics',

    // COMMON STORE SUBSCRIBTION ACTIONS
    SUBSCRIBTION_CASE_ID_CHANGED: Symbol('subscription-caseID-change'),
    SUBSCRIBTION_TAG_PATENT_ADDED: Symbol('subscription-tag-patent-added'),
    SUBSCRIBTION_TAG_PATENT_REMOVED: Symbol('subscription-tag-patent-removed'),
    SUBSCRIBTION_TAG_INFO_UPDATED: Symbol('subscription-tag-information-updated')
  };
});
//# sourceMappingURL=constants.js.map
