const form = document.querySelector("#metadata-form");

if (form) {
    const urlInput = form.querySelector("#media-url");
    const submitButton = form.querySelector("#metadata-submit");
    const status = document.querySelector("#metadata-status");
    const errorMessage = document.querySelector("#metadata-error");
    const preview = document.querySelector("#metadata-preview");
    const thumbnail = document.querySelector("#preview-thumbnail");
    const title = document.querySelector("#preview-title");
    const duration = document.querySelector("#preview-duration");
    const downloadForm = document.querySelector("#download-form");
    const mediaTypeSelect = document.querySelector("#media-type");
    const formatSelect = document.querySelector("#download-format");
    const qualityGroup = document.querySelector("#quality-group");
    const qualityLabel = document.querySelector("#quality-label");
    const qualitySelect = document.querySelector("#download-quality");
    const downloadButton = document.querySelector("#download-submit");
    const downloadFileLink = document.querySelector("#download-file-link");
    const downloadStatus = document.querySelector("#download-status");
    const downloadError = document.querySelector("#download-error");
    const progressPanel = document.querySelector("#download-progress-panel");
    const progressLabel = document.querySelector("#download-progress-label");
    const progressPercent = document.querySelector("#download-progress-percent");
    const progressBar = document.querySelector("#download-progress");
    const progressDetails = document.querySelector("#download-progress-details");
    const buttonLabel = submitButton.textContent.trim();
    const downloadButtonLabel = downloadButton.textContent.trim();
    let currentMetadata = null;
    let activeTaskId = null;
    let pollingTimer = null;

    const audioFormats = [
        ["mp3", "MP3"],
        ["m4a", "M4A"],
        ["flac", "FLAC"],
        ["wav", "WAV"],
        ["opus", "Opus"],
    ];

    function setSelectOptions(select, options, selectedValue) {
        select.replaceChildren(
            ...options.map(([value, label]) => new Option(label, value)),
        );
        select.value = selectedValue;
    }

    function formatDuration(value) {
        if (value === null || value === undefined || value === "") {
            return null;
        }

        const totalSeconds = Math.floor(Number(value));
        if (!Number.isFinite(totalSeconds) || totalSeconds < 0) {
            return null;
        }

        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        if (hours > 0) {
            return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
        }

        return `${minutes}:${String(seconds).padStart(2, "0")}`;
    }

    function formatBytes(value) {
        if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
            return null;
        }

        const units = ["B", "KB", "MB", "GB", "TB"];
        let size = value;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex += 1;
        }

        const decimals = unitIndex === 0 ? 0 : 1;
        return `${size.toFixed(decimals)} ${units[unitIndex]}`;
    }

    function getThumbnailUrl(value) {
        if (typeof value !== "string" || !value) {
            return null;
        }

        try {
            const url = new URL(value);
            if (url.protocol === "https:" && url.hostname.endsWith(".ytimg.com")) {
                return url.href;
            }
        } catch {
            return null;
        }

        return null;
    }

    function getAvailableResolutions() {
        const formats = Array.isArray(currentMetadata?.formats)
            ? currentMetadata.formats
            : [];
        return [...new Set(
            formats
                .filter((item) => item && typeof item === "object" && (
                    Number.isInteger(item.height)
                    && item.height > 0
                    && typeof item.video_codec === "string"
                    && item.video_codec !== "none"
                ))
                .map((item) => item.height),
        )].sort((a, b) => b - a);
    }

    function updateQualityOptions() {
        const mediaType = mediaTypeSelect.value;
        if (mediaType === "audio" && formatSelect.value === "mp3") {
            qualityGroup.hidden = false;
            qualityLabel.textContent = "Qualidade MP3 (kbps)";
            qualitySelect.disabled = downloadButton.disabled;
            setSelectOptions(
                qualitySelect,
                [["128", "128 kbps"], ["192", "192 kbps"], ["320", "320 kbps"]],
                "192",
            );
            return;
        }

        if (mediaType === "video") {
            qualityGroup.hidden = false;
            qualityLabel.textContent = "Resolução";
            qualitySelect.disabled = downloadButton.disabled;
            const options = [["auto", "Automática (melhor disponível)"]];
            options.push(
                ...getAvailableResolutions().map((height) => [
                    String(height),
                    `${height}p`,
                ]),
            );
            setSelectOptions(qualitySelect, options, "auto");
            return;
        }

        qualityGroup.hidden = true;
        qualitySelect.disabled = true;
        qualitySelect.replaceChildren();
    }

    function updateDownloadOptions() {
        if (mediaTypeSelect.value === "video") {
            setSelectOptions(formatSelect, [["mp4", "MP4"]], "mp4");
        } else {
            setSelectOptions(formatSelect, audioFormats, "mp3");
        }
        formatSelect.disabled = downloadButton.disabled;
        updateQualityOptions();
    }

    function resetProgress() {
        downloadStatus.textContent = "";
        downloadError.textContent = "";
        downloadError.hidden = true;
        downloadButton.hidden = false;
        downloadFileLink.hidden = true;
        downloadFileLink.removeAttribute("href");
        progressPanel.hidden = true;
        progressLabel.textContent = "Aguardando progresso...";
        progressPercent.textContent = "";
        progressBar.removeAttribute("value");
        progressDetails.textContent = "";
    }

    function setDownloadBusy(isBusy) {
        urlInput.disabled = isBusy;
        submitButton.disabled = isBusy;
        mediaTypeSelect.disabled = isBusy;
        formatSelect.disabled = isBusy;
        qualitySelect.disabled = isBusy || qualityGroup.hidden;
        downloadButton.disabled = isBusy;
        downloadButton.textContent = isBusy ? "Download em andamento..." : downloadButtonLabel;
        if (isBusy) {
            form.setAttribute("aria-busy", "true");
            downloadForm.setAttribute("aria-busy", "true");
        } else {
            form.removeAttribute("aria-busy");
            downloadForm.removeAttribute("aria-busy");
        }
    }

    function renderProgress(task) {
        const progress = task.progress && typeof task.progress === "object"
            ? task.progress
            : null;
        progressPanel.hidden = false;

        if (task.status === "queued") {
            progressLabel.textContent = "Aguardando na fila...";
        } else if (task.status === "failed") {
            progressLabel.textContent = "Falhou";
        } else if (task.status === "completed") {
            progressLabel.textContent = "Concluído";
        } else if (progress?.status === "finished") {
            progressLabel.textContent = "Processando arquivo...";
        } else {
            progressLabel.textContent = "Download em andamento...";
        }

        if (typeof progress?.percentage === "number" && Number.isFinite(progress.percentage)) {
            const percentage = Math.min(100, Math.max(0, progress.percentage));
            progressBar.value = percentage;
            progressPercent.textContent = `${Math.round(percentage)}%`;
        } else {
            progressBar.removeAttribute("value");
            progressPercent.textContent = "";
        }

        const details = [];
        const downloaded = formatBytes(progress?.downloaded_bytes);
        const total = formatBytes(progress?.total_bytes);
        const speed = formatBytes(progress?.speed);
        const eta = formatDuration(progress?.eta);
        if (downloaded && total) {
            details.push(`${downloaded} de ${total}`);
        } else if (downloaded) {
            details.push(`${downloaded} baixados`);
        }
        if (speed) {
            details.push(`${speed}/s`);
        }
        if (eta) {
            details.push(`restam ${eta}`);
        }
        progressDetails.textContent = details.join(" · ");
    }

    function finishDownload(errorMessage = null) {
        if (pollingTimer !== null) {
            clearTimeout(pollingTimer);
            pollingTimer = null;
        }
        activeTaskId = null;
        setDownloadBusy(false);

        if (errorMessage) {
            downloadButton.hidden = false;
            progressLabel.textContent = "Falhou";
            downloadStatus.textContent = "O download não foi concluído.";
            downloadError.textContent = errorMessage;
            downloadError.hidden = false;
            downloadFileLink.hidden = true;
            downloadFileLink.removeAttribute("href");
        } else {
            downloadButton.hidden = true;
            downloadStatus.textContent = "Download concluído.";
        }
    }

    function getResponseError(result, fallbackMessage) {
        if (typeof result?.error === "string") {
            return result.error;
        }
        return result?.error?.message || fallbackMessage;
    }

    async function requestJson(endpoint, options, fallbackMessage) {
        let response;
        try {
            response = await fetch(endpoint, options);
        } catch {
            throw new Error("Não foi possível conectar ao servidor.");
        }

        let result;
        try {
            result = await response.json();
        } catch {
            throw new Error("O servidor retornou uma resposta inválida.");
        }

        if (!response.ok) {
            throw new Error(getResponseError(result, fallbackMessage));
        }
        if (!result || result.success !== true) {
            throw new Error(fallbackMessage);
        }
        return result;
    }

    async function pollProgress(taskId) {
        if (activeTaskId !== taskId) {
            return;
        }

        const endpoint = downloadForm.dataset.progressEndpointTemplate.replace(
            "__TASK_ID__",
            encodeURIComponent(taskId),
        );

        try {
            const result = await requestJson(
                endpoint,
                { headers: { "Accept": "application/json" } },
                "Não foi possível consultar o progresso.",
            );
            const task = result.task;
            if (!task || task.id !== taskId) {
                throw new Error("O servidor retornou o estado da tarefa inválido.");
            }

            renderProgress(task);
            if (task.status === "completed") {
                progressBar.value = 100;
                progressPercent.textContent = "100%";
                progressLabel.textContent = "Concluído";
                downloadFileLink.href = downloadForm.dataset.fileEndpointTemplate.replace(
                    "__TASK_ID__",
                    encodeURIComponent(taskId),
                );
                downloadFileLink.hidden = false;
                finishDownload();
                return;
            }
            if (task.status === "failed") {
                finishDownload(task.error || "Não foi possível concluir o download.");
                return;
            }
            if (task.status !== "queued" && task.status !== "running") {
                throw new Error("O servidor retornou um estado de tarefa desconhecido.");
            }

            pollingTimer = setTimeout(() => pollProgress(taskId), 1000);
        } catch (error) {
            finishDownload(
                error instanceof Error
                    ? error.message
                    : "Não foi possível consultar o progresso.",
            );
        }
    }

    function showMetadata(metadata) {
        currentMetadata = metadata;
        title.textContent = metadata.title || "Título indisponível";

        const thumbnailUrl = getThumbnailUrl(metadata.thumbnail);
        thumbnail.hidden = !thumbnailUrl;
        thumbnail.alt = thumbnailUrl ? `Thumbnail de ${title.textContent}` : "";
        if (thumbnailUrl) {
            thumbnail.src = thumbnailUrl;
        } else {
            thumbnail.removeAttribute("src");
        }

        const formattedDuration = formatDuration(metadata.duration);
        duration.textContent = formattedDuration
            ? `Duração: ${formattedDuration}`
            : "Duração indisponível";

        preview.hidden = false;
        updateDownloadOptions();
        downloadForm.hidden = false;
    }

    urlInput.addEventListener("input", () => {
        errorMessage.hidden = true;
        status.textContent = "";
        preview.hidden = true;
        downloadForm.hidden = true;
        currentMetadata = null;
        resetProgress();
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) {
            return;
        }

        errorMessage.hidden = true;
        preview.hidden = true;
        downloadForm.hidden = true;
        currentMetadata = null;
        resetProgress();
        status.textContent = "Identificando conteúdo...";
        submitButton.disabled = true;
        submitButton.textContent = "Aguarde...";
        urlInput.disabled = true;
        form.setAttribute("aria-busy", "true");

        try {
            let response;
            try {
                response = await fetch(form.dataset.endpoint, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    body: JSON.stringify({ url: urlInput.value.trim() }),
                });
            } catch {
                throw new Error("Não foi possível conectar ao servidor.");
            }

            let result;
            try {
                result = await response.json();
            } catch {
                throw new Error("O servidor retornou uma resposta inválida.");
            }

            if (!response.ok) {
                const message = typeof result.error === "string"
                    ? result.error
                    : result.error?.message;
                throw new Error(message || "Não foi possível identificar o conteúdo.");
            }
            if (result.success !== true || !result.metadata) {
                throw new Error("O servidor retornou metadados incompletos.");
            }

            showMetadata(result.metadata);
            status.textContent = "Conteúdo identificado.";
        } catch (error) {
            errorMessage.textContent = error instanceof Error
                ? error.message
                : "Não foi possível conectar ao servidor.";
            errorMessage.hidden = false;
            status.textContent = "";
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = buttonLabel;
            urlInput.disabled = false;
            form.removeAttribute("aria-busy");
        }
    });

    mediaTypeSelect.addEventListener("change", updateDownloadOptions);
    formatSelect.addEventListener("change", updateQualityOptions);

    downloadForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!currentMetadata || activeTaskId) {
            return;
        }

        downloadError.hidden = true;
        downloadError.textContent = "";
        downloadFileLink.hidden = true;
        downloadFileLink.removeAttribute("href");
        downloadStatus.textContent = "Iniciando download...";
        progressPanel.hidden = false;
        progressBar.removeAttribute("value");
        progressPercent.textContent = "";
        progressDetails.textContent = "";
        progressLabel.textContent = "Aguardando na fila...";
        setDownloadBusy(true);

        const mediaType = mediaTypeSelect.value;
        const options = {
            url: urlInput.value.trim(),
            media_type: mediaType,
            format: formatSelect.value,
            quality: qualityGroup.hidden ? null : qualitySelect.value,
        };

        try {
            const result = await requestJson(
                downloadForm.dataset.endpoint,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    body: JSON.stringify(options),
                },
                "Não foi possível iniciar o download.",
            );

            if (typeof result.task?.id !== "string") {
                throw new Error("O servidor não retornou o identificador da tarefa.");
            }
            activeTaskId = result.task.id;
            await pollProgress(activeTaskId);
        } catch (error) {
            finishDownload(
                error instanceof Error
                    ? error.message
                    : "Não foi possível iniciar o download.",
            );
        }
    });
}
