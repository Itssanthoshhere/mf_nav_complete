// =============================================================================
// MF NAV Power Query — Complete Collection
// =============================================================================
// Contains 4 separate queries. In Excel/Power BI, create a Blank Query for
// each one and paste the corresponding block into Advanced Editor.
//
// QUERIES:
//   Q1 — AMFI Bulk Latest NAV       (all ~15k schemes, single request, fast)
//   Q2 — Single Scheme Full History  (change scheme_code variable)
//   Q3 — Search Schemes by Name      (filter from Q1)
//   Q4 — Load from Python CSV        (if you ran the Python scripts)
// =============================================================================


// =============================================================================
// QUERY 1: AMFI Bulk Latest NAV
// Name this query: MF_Latest_NAV
// =============================================================================
// Paste this into a new Blank Query → Advanced Editor
// Refresh to get live data every time you click "Refresh All"
// =============================================================================

let
    // ── Fetch raw text from AMFI ──────────────────────────────────────────────
    RawText = Text.FromBinary(
        Web.Contents(
            "https://www.amfiindia.com/spages/NAVAll.txt",
            [Timeout = #duration(0, 0, 0, 30)]
        )
    ),

    // ── Split into lines ──────────────────────────────────────────────────────
    Lines = Lines.FromText(RawText),

    // ── Keep only lines that contain semicolons (data rows) ──────────────────
    DataLines = List.Select(Lines, each Text.Contains(_, ";")),

    // ── Split each line by semicolon ──────────────────────────────────────────
    SplitLines = List.Transform(DataLines, each Text.Split(_, ";")),

    // ── Filter: must have at least 5 fields, first field must be numeric ──────
    ValidLines = List.Select(SplitLines, each
        List.Count(_) >= 5 and
        Value.Is(Value.FromText(List.First(_)), type number)
    ),

    // ── Build table ───────────────────────────────────────────────────────────
    RawTable = Table.FromRows(
        ValidLines,
        {"SchemeCode", "ISINGrowth", "ISINDivReinvestment", "SchemeName", "NAV", "Date"}
    ),

    // ── Type conversions ──────────────────────────────────────────────────────
    Typed = Table.TransformColumnTypes(
        RawTable,
        {
            {"SchemeCode", Int64.Type},
            {"NAV",        type number},
            {"ISINGrowth", type text},
            {"ISINDivReinvestment", type text},
            {"SchemeName", type text},
            {"Date",       type text}
        }
    ),

    // ── Parse Date: AMFI format is DD-MMM-YYYY (e.g. "03-Jun-2025") ──────────
    WithDate = Table.AddColumn(
        Typed, "NavDate",
        each
            let
                d = [Date]
            in
                try Date.FromText(d) otherwise
                try Date.FromText(
                    Text.Combine(List.Reverse(Text.Split(d, "-")), "-")
                ) otherwise null,
        type date
    ),

    // ── Clean up ──────────────────────────────────────────────────────────────
    Final = Table.RemoveColumns(WithDate, {"Date"}),

    Reordered = Table.ReorderColumns(
        Final,
        {"SchemeCode", "SchemeName", "NAV", "NavDate",
         "ISINGrowth", "ISINDivReinvestment"}
    ),

    Sorted = Table.Sort(Reordered, {{"SchemeName", Order.Ascending}})

in
    Sorted


// =============================================================================
// QUERY 2: Single Scheme Full NAV History
// Name this query: MF_SchemeHistory
// =============================================================================
// Change the schemeCode value below to any valid scheme code.
// Find scheme codes by searching in Query 1 or at mfapi.in
// =============================================================================

/*

let
    // ─── CHANGE THIS ────────────────────────────────────────────────────────
    schemeCode = 125497,    // HDFC Top 100 Fund - Direct Plan - Growth
    // ────────────────────────────────────────────────────────────────────────

    Url = "https://api.mfapi.in/mf/" & Number.ToText(schemeCode),

    Raw  = Json.Document(Web.Contents(Url, [Timeout = #duration(0, 0, 0, 20)])),

    // ── Metadata ──────────────────────────────────────────────────────────────
    Meta = Raw[meta],

    // ── NAV history list ──────────────────────────────────────────────────────
    DataList = Raw[data],

    HistTable = Table.FromList(
        DataList,
        Splitter.SplitByNothing(),
        null, null, ExtraValues.Error
    ),

    Expanded = Table.ExpandRecordColumn(
        HistTable, "Column1",
        {"date", "nav"},
        {"RawDate", "NAV"}
    ),

    // ── Parse date (mfapi format: DD-MM-YYYY) ─────────────────────────────────
    WithDate = Table.AddColumn(
        Expanded, "NavDate",
        each Date.FromText(
            Text.Combine(
                List.Reverse(Text.Split([RawDate], "-")),
                "-"
            )
        ),
        type date
    ),

    // ── Add metadata columns ──────────────────────────────────────────────────
    WithMeta = Table.AddColumn(WithDate,     "SchemeCode",     each schemeCode, Int64.Type),
    WithMeta2 = Table.AddColumn(WithMeta,    "SchemeName",     each Meta[scheme_name], type text),
    WithMeta3 = Table.AddColumn(WithMeta2,   "FundHouse",      each Meta[fund_house], type text),
    WithMeta4 = Table.AddColumn(WithMeta3,   "SchemeType",     each Meta[scheme_type], type text),
    WithMeta5 = Table.AddColumn(WithMeta4,   "SchemeCategory", each Meta[scheme_category], type text),

    Typed = Table.TransformColumnTypes(
        WithMeta5,
        {{"NAV", type number}}
    ),

    Cleaned = Table.RemoveColumns(Typed, {"RawDate"}),

    Reordered = Table.ReorderColumns(
        Cleaned,
        {"SchemeCode", "SchemeName", "FundHouse", "SchemeType",
         "SchemeCategory", "NavDate", "NAV"}
    ),

    Sorted = Table.Sort(Reordered, {{"NavDate", Order.Ascending}})

in
    Sorted

*/


// =============================================================================
// QUERY 3: Filter by Fund House (reference Query 1)
// Name this query: MF_HDFCSchemes  (rename as needed)
// =============================================================================
// This references MF_Latest_NAV — make sure that query is created first.
// Change the fund house filter string as needed.
// =============================================================================

/*

let
    Source    = MF_Latest_NAV,
    Filtered  = Table.SelectRows(
        Source,
        each Text.Contains([SchemeName], "HDFC", Comparer.OrdinalIgnoreCase)
            // Add more:
            // or Text.Contains([SchemeName], "SBI", Comparer.OrdinalIgnoreCase)
    )
in
    Filtered

*/


// =============================================================================
// QUERY 4: Load from Python-generated CSV
// Name this query: MF_FromCSV
// =============================================================================
// Use this if you ran the Python scripts and want to load the output CSV.
// Change the file path below.
// =============================================================================

/*

let
    // ─── CHANGE THIS PATH ───────────────────────────────────────────────────
    FilePath = "C:\Users\YourName\mf_nav_complete\data\latest_nav.csv",
    // On Mac:
    // FilePath = "/Users/yourname/mf_nav_complete/data/latest_nav.csv",
    // ────────────────────────────────────────────────────────────────────────

    Source = Csv.Document(
        File.Contents(FilePath),
        [Delimiter = ",", Columns = 7, Encoding = 65001, QuoteStyle = QuoteStyle.None]
    ),

    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"scheme_code", Int64.Type},
            {"nav",         type number},
            {"nav_date",    type datetime},
            {"scheme_name", type text},
            {"isin_growth", type text},
            {"isin_div",    type text},
            {"amc_section", type text}
        }
    )

in
    Typed

*/
