// This file centralizes all translatable strings for the UI to avoid circular dependencies.

// The `t` object is exported empty and will be populated by `initializeTranslations`.
export const t = {};

// This function populates the `t` object. It should be called once the global `_` function is available.
export function initializeTranslations() {
    Object.assign(t, {
        // General UI
        networkResponseNotOk: _('Network response was not ok.'),
        noChangesDetected: _('No changes detected.'),
        confirmDeleteBook: _('Are you sure you want to delete this book? This action cannot be undone.'),
        invalidPageNumber: _('Please enter a valid page number between 1 and %(totalPages)s.'),
        selectFilesToUpload: _('Please select files to upload.'),
        waiting: _('Waiting...'),
        uploading: _('Uploading...'),
        processing: _('Processing...'),
        uploadFailed: _('Upload failed'),
        networkError: _('Network Error'),
        NETWORK_ERROR: _('Network error: Failed to connect to the server.'),
        allBooksUploaded: _('All books uploaded successfully!'),
        someFilesFailedUpload: _('Some files failed to upload. Please check the progress details.'),
        generating: _('Generating...'),
        downloadAudiobook: _('Download Audiobook'),
        listenAudiobook: _('Listen to Audiobook'),
        failed: _('Failed'),
        error: _('Error'),
        success: _('Success!'),

        // Edit Modal
        title: _('Title'),
        author: _('Author'),
        authors: _('Authors (comma-separated)'),
        rating: _('Rating (0-5)'),
        readingProgress: _('Reading Progress (%)'),
        description: _('Description'),
        note: _('Note'),
        metadataNote: _('Metadata updates for Calibre books are asynchronous and may take a moment to apply.'),
        publisher: _('Publisher'),
        pubDate: _('Publication Date'),
        tags: _('Tags (comma-separated)'),
        library: _('Library (custom field #library)'),
        readDate: _('Read Date (custom field #readdate)'),

        // Audiobook Status Keys (from backend)
        QUEUED: _("Task queued"),
        GENERATION_STARTED: _("Starting audiobook generation..."),
        PARSING_EPUB: _("Parsing EPUB file..."),
        PROCESSING_CHAPTER: _("Processing: Chapter %(index)d/%(total)d"),
        MERGING_FILES: _("Merging audio files..."),
        WRITING_METADATA: _("Writing book metadata..."),
        CLEANING_UP: _("Cleaning up temporary files..."),
        GENERATION_SUCCESS: _("Audiobook generated successfully!"),
        CHAPTER_EXTRACTION_FAILED: _("Could not extract any chapters from the EPUB file."),
        CHAPTER_CONVERSION_FAILED: _("All chapters are empty or could not be converted to audio."),
        UNKNOWN_ERROR: _("An unknown error occurred: %(error)s"),
        FILE_ERROR: _("File error: %(error)s"),
    });
}