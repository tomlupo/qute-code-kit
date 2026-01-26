# Rockbridge TFI PDF Styles

Complete reference for generating branded PDF documents with Rockbridge TFI visual identity.

## Color Constants

Use these color values when generating PDFs:

```javascript
// JavaScript/TypeScript
const ROCKBRIDGE_COLORS = {
  primary: '#00A19A',
  primaryDark: '#008A84',
  primaryLight: '#33B5AF',
  dark: '#1D3D36',
  darkLight: '#2A5249',
  gold: '#C9A45C',
  goldLight: '#D4B978',
  goldSoft: '#F5EDD8',
  text: '#1A1A1A',
  textMuted: '#6B7280',
  white: '#FFFFFF',
  backgroundAlt: '#F5F7F6',
  surface: '#EEF2F0',
  border: '#E5E7EB',
  success: '#16A34A',
  error: '#DC2626',
  warning: '#D97706',
};
```

```python
# Python
ROCKBRIDGE_COLORS = {
    'primary': '#00A19A',
    'primary_dark': '#008A84',
    'primary_light': '#33B5AF',
    'dark': '#1D3D36',
    'dark_light': '#2A5249',
    'gold': '#C9A45C',
    'gold_light': '#D4B978',
    'gold_soft': '#F5EDD8',
    'text': '#1A1A1A',
    'text_muted': '#6B7280',
    'white': '#FFFFFF',
    'background_alt': '#F5F7F6',
    'surface': '#EEF2F0',
    'border': '#E5E7EB',
    'success': '#16A34A',
    'error': '#DC2626',
    'warning': '#D97706',
}
```

## Page Setup

### A4 Document

```javascript
// Dimensions in points (1 point = 1/72 inch)
const PAGE = {
  width: 595.28,  // A4 width
  height: 841.89, // A4 height
  margins: {
    top: 56.69,    // 20mm
    bottom: 56.69, // 20mm
    left: 42.52,   // 15mm
    right: 42.52,  // 15mm
  },
};
```

```python
# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 20 * mm
MARGIN_LEFT = 15 * mm
MARGIN_RIGHT = 15 * mm
```

## Typography Styles

### React-PDF StyleSheet

```jsx
import { StyleSheet } from '@react-pdf/renderer';

const styles = StyleSheet.create({
  // Page
  page: {
    backgroundColor: '#FFFFFF',
    fontFamily: 'Helvetica',
    padding: 20,
  },

  // Header
  header: {
    backgroundColor: '#1D3D36',
    padding: 15,
    marginHorizontal: -20,
    marginTop: -20,
    marginBottom: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: 'bold',
  },
  headerSubtext: {
    color: '#33B5AF',
    fontSize: 10,
  },

  // Footer
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#00A19A',
    padding: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  footerText: {
    color: '#FFFFFF',
    fontSize: 8,
  },
  pageNumber: {
    color: '#FFFFFF',
    fontSize: 8,
  },

  // Headings
  h1: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#00A19A',
    marginBottom: 16,
  },
  h2: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1D3D36',
    marginBottom: 12,
  },
  h3: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#1A1A1A',
    marginBottom: 8,
  },

  // Body text
  body: {
    fontSize: 10,
    color: '#1A1A1A',
    lineHeight: 1.5,
    marginBottom: 8,
  },
  bodySmall: {
    fontSize: 8,
    color: '#6B7280',
    lineHeight: 1.4,
  },

  // Legal/Disclaimer
  legal: {
    fontSize: 7,
    color: '#6B7280',
    lineHeight: 1.3,
    marginTop: 16,
  },

  // Sections
  section: {
    marginBottom: 20,
  },
  sectionDark: {
    backgroundColor: '#1D3D36',
    padding: 15,
    marginHorizontal: -20,
    marginBottom: 20,
  },
  sectionDarkText: {
    color: '#FFFFFF',
  },

  // Cards
  card: {
    backgroundColor: '#EEF2F0',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },

  // Tables
  table: {
    width: '100%',
  },
  tableHeader: {
    backgroundColor: '#1D3D36',
    flexDirection: 'row',
  },
  tableHeaderCell: {
    padding: 8,
    color: '#FFFFFF',
    fontSize: 9,
    fontWeight: 'bold',
  },
  tableRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  tableRowAlt: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
    backgroundColor: '#F5F7F6',
  },
  tableCell: {
    padding: 8,
    fontSize: 9,
    color: '#1A1A1A',
  },

  // Values
  positive: {
    color: '#16A34A',
  },
  negative: {
    color: '#DC2626',
  },

  // Risk indicator
  riskContainer: {
    flexDirection: 'row',
    gap: 2,
  },
  riskBox: {
    width: 24,
    height: 24,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    justifyContent: 'center',
    alignItems: 'center',
  },
  riskBoxActive: {
    backgroundColor: '#00A19A',
    borderColor: '#00A19A',
  },
  riskText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#1A1A1A',
  },
  riskTextActive: {
    color: '#FFFFFF',
  },

  // Awards/Gold section
  goldBadge: {
    backgroundColor: '#F5EDD8',
    padding: 8,
    borderRadius: 4,
  },
  goldText: {
    color: '#C9A45C',
    fontSize: 10,
    fontWeight: 'bold',
  },
});
```

### Python ReportLab Styles

```python
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# Colors
PRIMARY = HexColor('#00A19A')
DARK = HexColor('#1D3D36')
GOLD = HexColor('#C9A45C')
TEXT = HexColor('#1A1A1A')
TEXT_MUTED = HexColor('#6B7280')
WHITE = HexColor('#FFFFFF')
SUCCESS = HexColor('#16A34A')
ERROR = HexColor('#DC2626')

# Custom styles
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name='RockbridgeH1',
    fontName='Helvetica-Bold',
    fontSize=24,
    textColor=PRIMARY,
    spaceAfter=16,
    leading=28,
))

styles.add(ParagraphStyle(
    name='RockbridgeH2',
    fontName='Helvetica-Bold',
    fontSize=18,
    textColor=DARK,
    spaceAfter=12,
    leading=22,
))

styles.add(ParagraphStyle(
    name='RockbridgeH3',
    fontName='Helvetica-Bold',
    fontSize=14,
    textColor=TEXT,
    spaceAfter=8,
    leading=18,
))

styles.add(ParagraphStyle(
    name='RockbridgeBody',
    fontName='Helvetica',
    fontSize=10,
    textColor=TEXT,
    spaceAfter=8,
    leading=15,
))

styles.add(ParagraphStyle(
    name='RockbridgeSmall',
    fontName='Helvetica',
    fontSize=8,
    textColor=TEXT_MUTED,
    leading=11,
))

styles.add(ParagraphStyle(
    name='RockbridgeLegal',
    fontName='Helvetica',
    fontSize=7,
    textColor=TEXT_MUTED,
    leading=9,
    spaceBefore=16,
))

styles.add(ParagraphStyle(
    name='RockbridgePositive',
    fontName='Helvetica',
    fontSize=10,
    textColor=SUCCESS,
))

styles.add(ParagraphStyle(
    name='RockbridgeNegative',
    fontName='Helvetica',
    fontSize=10,
    textColor=ERROR,
))
```

## Component Templates

### React-PDF Fund Card

```jsx
import { Document, Page, Text, View, StyleSheet } from '@react-pdf/renderer';

const FundCard = ({ fundName, returns, riskLevel, fundInfo }) => (
  <Document>
    <Page size="A4" style={styles.page}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerText}>Rockbridge TFI</Text>
          <Text style={styles.headerSubtext}>Informacja reklamowa</Text>
        </View>
        {/* Logo placeholder */}
      </View>

      {/* Fund Name */}
      <Text style={styles.h1}>{fundName}</Text>

      {/* Returns Table */}
      <View style={styles.section}>
        <Text style={styles.h3}>Stopy zwrotu</Text>
        <View style={styles.table}>
          <View style={styles.tableHeader}>
            <Text style={[styles.tableHeaderCell, { flex: 1 }]}>Okres</Text>
            <Text style={[styles.tableHeaderCell, { flex: 1, textAlign: 'right' }]}>Fundusz</Text>
            <Text style={[styles.tableHeaderCell, { flex: 1, textAlign: 'right' }]}>Benchmark</Text>
          </View>
          {returns.map((row, i) => (
            <View key={i} style={i % 2 === 0 ? styles.tableRow : styles.tableRowAlt}>
              <Text style={[styles.tableCell, { flex: 1 }]}>{row.period}</Text>
              <Text style={[styles.tableCell, { flex: 1, textAlign: 'right' },
                row.fund >= 0 ? styles.positive : styles.negative]}>
                {row.fund >= 0 ? '+' : ''}{row.fund}%
              </Text>
              <Text style={[styles.tableCell, { flex: 1, textAlign: 'right' }]}>
                {row.benchmark}%
              </Text>
            </View>
          ))}
        </View>
      </View>

      {/* Risk Indicator */}
      <View style={styles.section}>
        <Text style={styles.h3}>Poziom ryzyka</Text>
        <View style={styles.riskContainer}>
          {[1, 2, 3, 4, 5, 6, 7].map(level => (
            <View
              key={level}
              style={[styles.riskBox, level === riskLevel && styles.riskBoxActive]}
            >
              <Text style={[styles.riskText, level === riskLevel && styles.riskTextActive]}>
                {level}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {/* Fund Info */}
      <View style={styles.section}>
        <Text style={styles.h3}>Informacje o funduszu</Text>
        {Object.entries(fundInfo).map(([key, value]) => (
          <View key={key} style={{ flexDirection: 'row', marginBottom: 4 }}>
            <Text style={[styles.bodySmall, { flex: 1 }]}>{key}</Text>
            <Text style={[styles.body, { flex: 1 }]}>{value}</Text>
          </View>
        ))}
      </View>

      {/* Legal Disclaimer */}
      <Text style={styles.legal}>
        Przedstawiony materia ma charakter reklamowy, nie stanowi uslugi doradztwa
        inwestycyjnego i nie nale??y go traktowa?? jako rekomendacji inwestowania
        w jakiekolwiek instrumenty finansowe. Wyniki historyczne nie stanowi??
        gwarancji osi??gni??cia podobnych zysk??w w przysz??o??ci.
      </Text>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>Infolinia: 801 350 000 | rockbridge.pl</Text>
        <Text render={({ pageNumber, totalPages }) =>
          `${pageNumber} / ${totalPages}`
        } style={styles.pageNumber} />
      </View>
    </Page>
  </Document>
);
```

### Python ReportLab Fund Card

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.colors import HexColor

def create_fund_card(filename, fund_data):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=20*mm,
        leftMargin=15*mm,
        rightMargin=15*mm,
    )

    story = []

    # Header (as table for layout)
    header_data = [['Rockbridge TFI', 'Informacja reklamowa']]
    header_table = Table(header_data, colWidths=[300, 180])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#1D3D36')),
        ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#FFFFFF')),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 14),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, 0), 10),
        ('TEXTCOLOR', (1, 0), (1, 0), HexColor('#33B5AF')),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (0, 0), 15),
        ('RIGHTPADDING', (-1, 0), (-1, 0), 15),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20))

    # Fund name
    story.append(Paragraph(fund_data['name'], styles['RockbridgeH1']))
    story.append(Spacer(1, 16))

    # Returns table
    story.append(Paragraph('Stopy zwrotu', styles['RockbridgeH3']))

    returns_data = [['Okres', 'Fundusz', 'Benchmark']]
    for row in fund_data['returns']:
        fund_val = f"+{row['fund']}%" if row['fund'] >= 0 else f"{row['fund']}%"
        returns_data.append([row['period'], fund_val, f"{row['benchmark']}%"])

    returns_table = Table(returns_data, colWidths=[100, 100, 100])
    returns_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1D3D36')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F5F7F6')]),
    ]))
    story.append(returns_table)
    story.append(Spacer(1, 20))

    # Risk indicator
    story.append(Paragraph('Poziom ryzyka', styles['RockbridgeH3']))

    risk_data = [[str(i) for i in range(1, 8)]]
    risk_table = Table(risk_data, colWidths=[24]*7)

    risk_style = [
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#E5E7EB')),
        ('INNERGRID', (0, 0), (-1, -1), 1, HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]

    # Highlight active risk level
    risk_level = fund_data.get('risk_level', 5)
    risk_style.append(('BACKGROUND', (risk_level-1, 0), (risk_level-1, 0), HexColor('#00A19A')))
    risk_style.append(('TEXTCOLOR', (risk_level-1, 0), (risk_level-1, 0), HexColor('#FFFFFF')))

    risk_table.setStyle(TableStyle(risk_style))
    story.append(risk_table)
    story.append(Spacer(1, 20))

    # Legal disclaimer
    story.append(Paragraph(
        """Przedstawiony materia ma charakter reklamowy, nie stanowi uslugi doradztwa
        inwestycyjnego i nie nale??y go traktowa?? jako rekomendacji inwestowania
        w jakiekolwiek instrumenty finansowe. Wyniki historyczne nie stanowi??
        gwarancji osi??gni??cia podobnych zysk??w w przysz??o??ci.""",
        styles['RockbridgeLegal']
    ))

    doc.build(story)

# Usage
fund_data = {
    'name': 'Rockbridge Akcji Globalnych',
    'returns': [
        {'period': '1M', 'fund': 1.72, 'benchmark': -3.36},
        {'period': '3M', 'fund': 3.74, 'benchmark': 3.24},
        {'period': '6M', 'fund': 10.43, 'benchmark': 9.48},
        {'period': '12M', 'fund': 18.61, 'benchmark': 18.23},
    ],
    'risk_level': 5,
}

create_fund_card('rockbridge_fund_card.pdf', fund_data)
```

## Chart Styling

### Performance Chart Colors

```javascript
const chartConfig = {
  // Bar chart (positive returns)
  barPositive: {
    backgroundColor: '#00A19A',
    borderColor: '#008A84',
    borderWidth: 1,
  },
  // Bar chart (negative returns)
  barNegative: {
    backgroundColor: '#DC2626',
    borderColor: '#B91C1C',
    borderWidth: 1,
  },
  // Line chart (fund performance)
  lineFund: {
    borderColor: '#00A19A',
    backgroundColor: 'rgba(0, 161, 154, 0.1)',
    borderWidth: 2,
    fill: true,
  },
  // Line chart (benchmark)
  lineBenchmark: {
    borderColor: '#1D3D36',
    borderWidth: 2,
    borderDash: [5, 5],
    fill: false,
  },
  // Grid
  grid: {
    color: '#E5E7EB',
  },
  // Axis labels
  axis: {
    color: '#6B7280',
    font: {
      family: 'Helvetica',
      size: 9,
    },
  },
};
```

## PDF Metadata

```javascript
// React-PDF
<Document
  title="Rockbridge Akcji Globalnych - Karta Funduszu"
  author="Rockbridge TFI S.A."
  subject="Informacja o funduszu inwestycyjnym"
  keywords="fundusz, inwestycje, Rockbridge, TFI"
  creator="Rockbridge TFI"
  producer="Rockbridge TFI Document Generator"
>
```

```python
# ReportLab
doc = SimpleDocTemplate(filename, pagesize=A4)
doc.title = "Rockbridge Akcji Globalnych - Karta Funduszu"
doc.author = "Rockbridge TFI S.A."
doc.subject = "Informacja o funduszu inwestycyjnym"
doc.keywords = "fundusz, inwestycje, Rockbridge, TFI"
```
