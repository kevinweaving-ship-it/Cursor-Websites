# PDF Conversion Rules

## Rule: Non-PDF Files Must Be Converted to PDF

**When scraping files from URL source:**
- If file is JPG/PNG/other image format → **MUST convert to PDF** before saving locally
- Conversion uses PIL/Pillow: `img.save(output_path, 'PDF', resolution=150.0)`
- Saved file extension: Always `.pdf` (regardless of source format)

## Conversion Process

1. **Download source file** (JPG/PNG/etc.) to temporary location
2. **Check file type** from `Content-Type` header or URL extension
3. **If not PDF**: Convert using `convert_to_pdf()` function
4. **Save as PDF** with hash-based filename
5. **Update database** with `local_file_path` and `file_type = 'pdf'`

## Image-Based PDFs

**Important Note:**
- Converting JPG/PNG to PDF creates an **image-based PDF** (embeds image in PDF format)
- Image-based PDFs are NOT searchable text PDFs
- Text extraction requires **OCR** (Optical Character Recognition)
- OCR quality depends on image resolution and quality

**Resolution Settings:**
- Current: `resolution=150.0` (improved from 100.0 for better OCR)
- Higher resolution = better OCR quality but larger file size
- Balance between quality and file size

## OCR Quality Issues

**If OCR quality is poor:**
1. Image resolution too low
2. Image quality/pixelation
3. Complex layouts/tables
4. Handwriting or unusual fonts

**Solutions:**
- Increase resolution in conversion (150.0 or higher)
- Image preprocessing before OCR
- Manual data entry (preferred for poor OCR)
- Use original source if available

## Example: Regatta 371

- Source: JPG from `sailing.org.za`
- Converted: Image-based PDF (conversion successful)
- OCR Result: Poor quality (garbled text, numbers unclear)
- Solution: Manual data entry required

## Validation

After conversion:
- ✅ File exists at `local_file_path`
- ✅ File type is `.pdf`
- ✅ File opens as PDF
- ⚠️ If OCR needed: Check quality before relying on extracted text



## Rule: Non-PDF Files Must Be Converted to PDF

**When scraping files from URL source:**
- If file is JPG/PNG/other image format → **MUST convert to PDF** before saving locally
- Conversion uses PIL/Pillow: `img.save(output_path, 'PDF', resolution=150.0)`
- Saved file extension: Always `.pdf` (regardless of source format)

## Conversion Process

1. **Download source file** (JPG/PNG/etc.) to temporary location
2. **Check file type** from `Content-Type` header or URL extension
3. **If not PDF**: Convert using `convert_to_pdf()` function
4. **Save as PDF** with hash-based filename
5. **Update database** with `local_file_path` and `file_type = 'pdf'`

## Image-Based PDFs

**Important Note:**
- Converting JPG/PNG to PDF creates an **image-based PDF** (embeds image in PDF format)
- Image-based PDFs are NOT searchable text PDFs
- Text extraction requires **OCR** (Optical Character Recognition)
- OCR quality depends on image resolution and quality

**Resolution Settings:**
- Current: `resolution=150.0` (improved from 100.0 for better OCR)
- Higher resolution = better OCR quality but larger file size
- Balance between quality and file size

## OCR Quality Issues

**If OCR quality is poor:**
1. Image resolution too low
2. Image quality/pixelation
3. Complex layouts/tables
4. Handwriting or unusual fonts

**Solutions:**
- Increase resolution in conversion (150.0 or higher)
- Image preprocessing before OCR
- Manual data entry (preferred for poor OCR)
- Use original source if available

## Example: Regatta 371

- Source: JPG from `sailing.org.za`
- Converted: Image-based PDF (conversion successful)
- OCR Result: Poor quality (garbled text, numbers unclear)
- Solution: Manual data entry required

## Validation

After conversion:
- ✅ File exists at `local_file_path`
- ✅ File type is `.pdf`
- ✅ File opens as PDF
- ⚠️ If OCR needed: Check quality before relying on extracted text


















