"""Restrict the existing 3D region and reuse Stage 3.4's resize listener."""

from src.gui.layout import Rect, calculate_layout, normalized_region


class DashboardViewport:
    """Borrow a live window/camera; own only dimensions and the provider binding.

    Intended for create_preview's full-window camera binding. ``on_refit`` must
    forward to the existing presentation's background and light-bound updates.
    No region, camera, listener, or graphics output is allocated here.
    """

    def __init__(self, window, camera_node, camera_controller, *, on_refit, on_layout):
        regions = [
            region
            for region in window.getDisplayRegions()
            if region.getCamera() == camera_node
        ]

        if len(regions) != 1:
            raise ValueError(
                "Expected exactly one existing main-camera DisplayRegion."
            )

        self.region = regions[0]
        self._original_dimensions = tuple(self.region.getDimensions())
        self._original_active = self.region.isActive()
        self._window, self._camera = window, camera_controller
        self._on_refit, self._on_layout = on_refit, on_layout
        self.layout = None
        self.region_override = None
        self._disposed = False

        try:
            camera_controller.bind_window(
                window,
                viewport_size=self._provide_size,
                on_refit=on_refit,
            )
            self.refresh()
        except BaseException:
            self.dispose()
            raise

    def _provide_size(self, window):
        width, height = window.getXSize(), window.getYSize()

        if width <= 0 or height <= 0:
            return 0, 0

        layout = calculate_layout(width, height)

        # ShowBase's own window handler may have overwritten the lens first.
        # Its aspectRatioChanged event calls this same provider, then refits.
        rect = layout.viewport

        if self.region_override is not None and layout.supported:
            rect = self.region_override(width, height)

        self.region.setDimensions(
            *normalized_region(rect, width, height)
        )
        self.region.setActive(
            self._original_active and layout.supported
        )

        if layout != self.layout:
            self._on_layout(layout)
            self.layout = layout

        return (rect.width, rect.height) if layout.supported else (0, 0)

    def refresh(self):
        """Explicit initial refresh; ordinary resizing uses the existing listener."""
        if self._disposed:
            return False

        return self._camera.set_viewport_size(
            *self._provide_size(self._window)
        )

    def set_region_override(self, function):
        self.region_override = function
        return self.refresh()

    def dispose(self, *, refit=True):
        """Restore full-window preview binding without destroying borrowed resources.

        Dashboard composition passes refit=False if the host already detached its
        scene. Dimensions/binding still restore, without touching dead light roots.
        If the presentation was already disposed, there is no listener to restore.
        """
        if self._disposed:
            return

        self._disposed = True

        self.region.setDimensions(*self._original_dimensions)
        self.region.setActive(self._original_active)

        if self._camera.camera is not None:
            self._camera.bind_window(
                self._window,
                on_refit=self._on_refit,
            )

            if refit:
                self._camera.set_viewport_size(
                    self._window.getXSize(),
                    self._window.getYSize(),
                )

        self._window = self._camera = self._on_refit = self._on_layout = None