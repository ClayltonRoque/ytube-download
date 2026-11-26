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
    const buttonLabel = submitButton.textContent.trim();

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

    function showMetadata(metadata) {
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
    }

    urlInput.addEventListener("input", () => {
        errorMessage.hidden = true;
        status.textContent = "";
        preview.hidden = true;
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) {
            return;
        }

        errorMessage.hidden = true;
        preview.hidden = true;
        status.textContent = "Identificando conteúdo...";
        submitButton.disabled = true;
        submitButton.textContent = "Aguarde...";
        form.setAttribute("aria-busy", "true");

        try {
            const response = await fetch(form.dataset.endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({ url: urlInput.value.trim() }),
            });

            let result;
            try {
                result = await response.json();
            } catch {
                throw new Error("O servidor retornou uma resposta inválida.");
            }

            if (!response.ok) {
                throw new Error(result.error || "Não foi possível identificar o conteúdo.");
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
            form.removeAttribute("aria-busy");
        }
    });
}
