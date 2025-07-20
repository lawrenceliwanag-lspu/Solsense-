import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
from tkinter import filedialog, messagebox, simpledialog
import rasterio
from rasterio.windows import Window
from rasterio.transform import Affine
from rasterio.crs import CRS
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
import matplotlib.patheffects as PathEffects
import urllib.request
import json
import datetime
import urllib.parse
import functools
import matplotlib.pyplot as plt
import csv


class GeoTIFFSlopeViewer:
    def __init__(self, master):
        self.master = master
        master.title("SolSense: GeoTIFF Slope Viewer")
        master.geometry("1200x900")
        master.configure(bg='#f0f0f0')

        # Modern color scheme
        self.colors = {
            'primary': '#2196F3',
            'primary_dark': '#1976D2',
            'secondary': '#FF9800',
            'success': '#4CAF50',
            'warning': '#FF5722',
            'background': '#fafafa',
            'surface': '#ffffff',
            'text_primary': '#212121',
            'text_secondary': '#757575',
            'border': '#e0e0e0',
            'accent': "#FFFFFF"
        }

        # Initialize data attributes
        self.filepath = None
        self.dataset = None
        self.slope_degrees = None
        self.aspect_degrees = None
        self.original_crs = None
        self.transform = None
        self.display_image_rgba = None
        self.nodata_value = None
        self.marker_pixel_coords = None
        self.marker_lon_lat = None
        self.marker_object = None
        self.land_area_rect_patch = None
        self.packed_object_patches = []
        self.pixel_width_m = 1.0
        self.pixel_height_m = 1.0

        # Configure modern styles
        self.setup_styles()

        # Create main layout
        self.create_main_layout()

        # Create controls
        self.create_controls()

        # Create map display
        self.create_map_display()

        # Create status bar
        self.create_status_bar()

    def setup_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()

        # Configure notebook style for tabs
        style.configure('Modern.TNotebook',
                       background=self.colors['surface'],
                       borderwidth=0)
        style.configure('Modern.TNotebook.Tab',
                       background=self.colors['background'],
                       foreground=self.colors['text_primary'],
                       padding=[20, 10],
                       focuscolor='none')
        style.map('Modern.TNotebook.Tab',
                 background=[('selected', self.colors['primary']),
                            ('active', self.colors['primary_dark'])],
                 foreground=[('selected', 'white'),
                            ('active', 'white')])

        # Configure button styles
        style.configure('Primary.TButton',
                       background=self.colors['primary'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=[20, 10])
        style.map('Primary.TButton',
                 background=[('active', self.colors['primary_dark']),
                            ('pressed', self.colors['primary_dark'])])

        style.configure('Secondary.TButton',
                       background=self.colors['secondary'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=[15, 8])
        style.map('Secondary.TButton',
                 background=[('active', '#F57C00'),
                            ('pressed', '#F57C00')])

        # Configure frame styles
        style.configure('Card.TFrame',
                       background=self.colors['surface'],
                       relief='flat',
                       borderwidth=1)

        # Configure labelframe styles
        style.configure('Modern.TLabelframe',
                       background=self.colors['surface'],
                       borderwidth=2,
                       relief='flat')
        style.configure('Modern.TLabelframe.Label',
                       background=self.colors['surface'],
                       foreground=self.colors['primary'],
                       font=('Segoe UI', 10, 'bold'))

        # Configure entry styles
        style.configure('Modern.TEntry',
                       fieldbackground='white',
                       borderwidth=1,
                       relief='solid',
                       padding=[10, 8])
        style.map('Modern.TEntry',
                 fieldbackground=[('readonly', '#f5f5f5')],
                 foreground=[('disabled', '#9e9e9e')],
                 bordercolor=[('focus', self.colors['primary'])])

    def create_main_layout(self):
        """Create the main layout structure"""

        # Main content area
        self.main_frame = tk.Frame(self.master, bg=self.colors['background'])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create main paned window
        self.main_pane = tk.PanedWindow(self.main_frame,
                                       orient=tk.HORIZONTAL,
                                       bg=self.colors['background'],
                                       sashwidth=8,
                                       sashrelief=tk.FLAT)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

    def create_controls(self):
        """Create the control panel with modern styling"""
        # Left panel container
        left_container = tk.Frame(self.main_pane, bg=self.colors['background'], width=400)
        left_container.pack_propagate(False)
        self.main_pane.add(left_container, stretch="never")

        # Scrollable area
        canvas_frame = tk.Frame(left_container, bg=self.colors['background'])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.controls_canvas = tk.Canvas(canvas_frame,
                                        bg=self.colors['background'],
                                        highlightthickness=0,
                                        borderwidth=0)

        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.controls_canvas.yview)
        self.scrollable_frame = tk.Frame(self.controls_canvas, bg=self.colors['background'])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.controls_canvas.configure(scrollregion=self.controls_canvas.bbox("all"))
        )

        self.controls_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.controls_canvas.configure(yscrollcommand=scrollbar.set)

        self.controls_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # File loading section
        self.create_file_section()

        # Packing and energy section
        self.create_packing_section()

        # Analysis results section
        self.create_results_section()

    def create_file_section(self):
        """Create the file loading section"""
        file_frame = ttk.Labelframe(self.scrollable_frame,
                                   text="📁 GeoTIFF File",
                                   style='Modern.TLabelframe',
                                   padding="15")
        file_frame.pack(fill=tk.X, pady=(0, 15), padx=10)

        # Load button
        self.btn_load = ttk.Button(file_frame,
                                  text="📂 Load GeoTIFF File",
                                  style='Primary.TButton',
                                  command=self.load_geotiff)
        self.btn_load.pack(pady=(0, 0), fill=tk.X)

        # File info
        self.lbl_file = tk.Label(file_frame,
                                text="No file loaded",
                                bg=self.colors['surface'],
                                fg=self.colors['text_secondary'],
                                font=('Segoe UI', 9))
        self.lbl_file.pack(pady=(0, 0))

        # File stats frame
        self.stats_frame = tk.Frame(file_frame, bg=self.colors['surface'])
        self.stats_frame.pack(fill=tk.X, pady=(0, 0))

    def create_packing_section(self):
        """Create the packing and energy analysis section"""

        pack_frame = ttk.Labelframe(self.scrollable_frame,
                                   text="⚡ Solar Panel Analysis",
                                   style='Modern.TLabelframe',
                                   padding="15")
        pack_frame.pack(fill=tk.X, pady=(0, 15), padx=10)

        # Marker section
        marker_section = tk.Frame(pack_frame, bg=self.colors['surface'])
        marker_section.pack(fill=tk.X, pady=(0, 15))

        marker_title = tk.Label(marker_section,
                               text="📍 Location Marker",
                               bg=self.colors['surface'],
                               fg=self.colors['text_primary'],
                               font=('Segoe UI', 9, 'bold'))
        marker_title.pack(anchor=tk.W, pady=(0, 5))

        self.lbl_marker_coords = tk.Label(marker_section,
                                         text="Coordinates: Not set",
                                         bg=self.colors['surface'],
                                         fg=self.colors['text_secondary'],
                                         font=('Segoe UI', 8))
        self.lbl_marker_coords.pack(anchor=tk.W)

        ttk.Button(marker_section, text="🧹 Clear", style='Secondary.TButton',
                   command=self.clear_marker_and_packing).pack(anchor='e', pady=(0, 5))

        # Separator
        separator1 = ttk.Separator(pack_frame, orient='horizontal')
        separator1.pack(fill=tk.X, pady=(0, 15))

        # Land dimensions
        land_section = tk.Frame(pack_frame, bg=self.colors['surface'])
        land_section.pack(fill=tk.X, pady=(0, 15))

        land_title = tk.Label(land_section,
                             text="🏞️ Land Dimensions",
                             bg=self.colors['surface'],
                             fg=self.colors['text_primary'],
                             font=('Segoe UI', 9, 'bold'))
        land_title.pack(anchor=tk.W, pady=(0, 10))

        # Width input
        width_frame = tk.Frame(land_section, bg=self.colors['surface'])
        width_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(width_frame, text="Width (m):", bg=self.colors['surface'],
                fg=self.colors['text_primary'], font=('Segoe UI', 8)).pack(side=tk.LEFT)
        self.entry_land_width = ttk.Entry(width_frame, style='Modern.TEntry', width=15)
        self.entry_land_width.insert(0, "100")
        self.entry_land_width.pack(side=tk.RIGHT)

        # Height input
        height_frame = tk.Frame(land_section, bg=self.colors['surface'])
        height_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(height_frame, text="Length/Depth (m):", bg=self.colors['surface'],
                fg=self.colors['text_primary'], font=('Segoe UI', 8)).pack(side=tk.LEFT)
        self.entry_land_height = ttk.Entry(height_frame, style='Modern.TEntry', width=15)
        self.entry_land_height.insert(0, "50")
        self.entry_land_height.pack(side=tk.RIGHT)

        # Separator
        separator2 = ttk.Separator(pack_frame, orient='horizontal')
        separator2.pack(fill=tk.X, pady=(0, 15))

        # Panel specifications
        panel_section = tk.Frame(pack_frame, bg=self.colors['surface'])
        panel_section.pack(fill=tk.X, pady=(0, 15))

        panel_title = tk.Label(panel_section,
                              text="☀️ Panel Specifications",
                              bg=self.colors['surface'],
                              fg=self.colors['text_primary'],
                              font=('Segoe UI', 9, 'bold'))
        panel_title.pack(anchor=tk.W, pady=(0, 10))

        # Panel dimensions
        panel_width_frame = tk.Frame(panel_section, bg=self.colors['surface'])
        panel_width_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(panel_width_frame, text="Panel Width (m):", bg=self.colors['surface'],
                fg=self.colors['text_primary'], font=('Segoe UI', 8)).pack(side=tk.LEFT)
        self.entry_obj_width = ttk.Entry(panel_width_frame, style='Modern.TEntry', width=15)
        self.entry_obj_width.insert(0, "1.65")
        self.entry_obj_width.pack(side=tk.RIGHT)

        panel_height_frame = tk.Frame(panel_section, bg=self.colors['surface'])
        panel_height_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(panel_height_frame, text="Panel Height (m):", bg=self.colors['surface'],
                fg=self.colors['text_primary'], font=('Segoe UI', 8)).pack(side=tk.LEFT)
        self.entry_obj_height = ttk.Entry(panel_height_frame, style='Modern.TEntry', width=15)
        self.entry_obj_height.insert(0, "1.0")
        self.entry_obj_height.pack(side=tk.RIGHT)

        # Packing mode
        pack_mode_frame = tk.Frame(panel_section, bg=self.colors['surface'])
        pack_mode_frame.pack(fill=tk.X, pady=(10, 0))

        self.pack_mode = tk.StringVar(value="fill")

        mode_title = tk.Label(pack_mode_frame,
                             text="Packing Mode:",
                             bg=self.colors['surface'],
                             fg=self.colors['text_primary'],
                             font=('Segoe UI', 8, 'bold'))
        mode_title.pack(anchor=tk.W, pady=(0, 5))

        radio_frame = tk.Frame(pack_mode_frame, bg=self.colors['surface'])
        radio_frame.pack(fill=tk.X)

        tk.Radiobutton(radio_frame, text="Fill maximum panels",
                      variable=self.pack_mode, value="fill",
                      bg=self.colors['surface'], fg=self.colors['text_primary'],
                      font=('Segoe UI', 8), selectcolor=self.colors['accent']).pack(anchor=tk.W)

        tk.Radiobutton(radio_frame, text="Specify number:",
                      variable=self.pack_mode, value="specify",
                      bg=self.colors['surface'], fg=self.colors['text_primary'],
                      font=('Segoe UI', 8), selectcolor=self.colors['accent']).pack(anchor=tk.W)

        num_frame = tk.Frame(radio_frame, bg=self.colors['surface'])
        num_frame.pack(fill=tk.X, padx=20)
        tk.Label(num_frame, text="Number:", bg=self.colors['surface'],
                fg=self.colors['text_primary'], font=('Segoe UI', 8)).pack(side=tk.LEFT)
        self.entry_num_objects = ttk.Entry(num_frame, style='Modern.TEntry', width=10)
        self.entry_num_objects.insert(0, "10")
        self.entry_num_objects.pack(side=tk.RIGHT)

        # Separator
        separator3 = ttk.Separator(pack_frame, orient='horizontal')
        separator3.pack(fill=tk.X, pady=(15, 15))

        # Performance parameters
        perf_section = tk.Frame(pack_frame, bg=self.colors['surface'])
        perf_section.pack(fill=tk.X, pady=(0, 15))

        perf_title = tk.Label(perf_section,
                             text="⚙️ Performance Parameters",
                             bg=self.colors['surface'],
                             fg=self.colors['text_primary'],
                             font=('Segoe UI', 9, 'bold'))
        perf_title.pack(anchor=tk.W, pady=(0, 10))

        # Efficiency
        eff_frame = tk.Frame(perf_section, bg=self.colors['surface'])
        eff_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(eff_frame, text="Panel Efficiency (%):", bg=self.colors['surface'],
                fg=self.colors['text_primary'], font=('Segoe UI', 8)).pack(side=tk.LEFT)
        self.entry_panel_efficiency = ttk.Entry(eff_frame, style='Modern.TEntry', width=15)
        self.entry_panel_efficiency.insert(0, "18")
        self.entry_panel_efficiency.pack(side=tk.RIGHT)

        # Performance ratio
        ratio_frame = tk.Frame(perf_section, bg=self.colors['surface'])
        ratio_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(ratio_frame, text="Performance Ratio:", bg=self.colors['surface'],
                fg=self.colors['text_primary'], font=('Segoe UI', 8)).pack(side=tk.LEFT)
        self.entry_perf_ratio = ttk.Entry(ratio_frame, style='Modern.TEntry', width=15)
        self.entry_perf_ratio.insert(0, "0.8")
        self.entry_perf_ratio.pack(side=tk.RIGHT)

        separator4 = ttk.Separator(pack_frame, orient='horizontal')
        separator4.pack(fill=tk.X, pady=(15, 15))

        # Run analysis button
        self.btn_run_packing = ttk.Button(pack_frame,
                                         text="🔄 Run Analysis",
                                         style='Secondary.TButton',
                                         command=self.run_packing_and_energy_simulation)
        self.btn_run_packing.pack(pady=(5, 0), fill=tk.X)

    def create_results_section(self):
        """Create the results display section"""
        results_frame = ttk.Labelframe(self.scrollable_frame,
                                      text="📊 Analysis Results",
                                      style='Modern.TLabelframe',
                                      padding="15")
        results_frame.pack(fill=tk.X, pady=(0, 15), padx=10)

        # Results container
        self.results_container = tk.Frame(results_frame, bg=self.colors['surface'])
        self.results_container.pack(fill=tk.X)

        # Packing results
        self.lbl_panels_packed = tk.Label(self.results_container,
                                       text="📦 Panels Packed: Not calculated",
                                       bg=self.colors['surface'],
                                       fg=self.colors['text_secondary'],
                                       font=('Segoe UI', 9))
        self.lbl_panels_packed.pack(anchor=tk.W, pady=(0, 8))

        # Energy results
        self.lbl_annual_energy = tk.Label(self.results_container,
                                         text="⚡ Annual Energy: Not calculated",
                                         bg=self.colors['surface'],
                                         fg=self.colors['text_secondary'],
                                         font=('Segoe UI', 9))
        self.lbl_annual_energy.pack(anchor=tk.W, pady=(0, 8))

        # Export button
        ttk.Button(self.results_container, text="💾 Export CSV",
                   command=self.export_results_csv).pack(anchor='e', pady=(10,0))

        # Additional stats placeholder
        self.lbl_additional_stats = tk.Label(self.results_container,
                                            text="",
                                            bg=self.colors['surface'],
                                            fg=self.colors['text_secondary'],
                                            font=('Segoe UI', 8))
        self.lbl_additional_stats.pack(anchor=tk.W)

    def create_map_display(self):
        """Create the map display area"""
        # Right panel for map
        right_frame = tk.Frame(self.main_pane, bg=self.colors['surface'])
        self.main_pane.add(right_frame, stretch="always")

        # Map container with modern styling
        map_container = tk.Frame(right_frame, bg=self.colors['surface'],
                                relief=tk.FLAT, borderwidth=2)
        map_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Map title
        map_title = tk.Label(map_container,
                            text="🗺️ Geographic Analysis View",
                            bg=self.colors['surface'],
                            fg=self.colors['text_primary'],
                            font=('Segoe UI', 12, 'bold'))
        map_title.pack(pady=(10, 5))

        # Map canvas
        self.fig = Figure(figsize=(10, 8), facecolor=self.colors['surface'])
        self.fig.patch.set_facecolor(self.colors['surface'])
        self.ax = self.fig.add_subplot(111)

        # Style the matplotlib figure
        self.ax.set_facecolor('#fafafa')
        self.ax.grid(True, alpha=0.3)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color('#e0e0e0')
        self.ax.spines['left'].set_color('#e0e0e0')

        self.canvas = FigureCanvasTkAgg(self.fig, master=map_container)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Toolbar
        toolbar_frame = tk.Frame(map_container, bg=self.colors['surface'])
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(side=tk.LEFT)

        # Connect click event
        self.fig.canvas.mpl_connect('button_press_event', self.on_click_map)

    def create_status_bar(self):
        """Create the status bar at the bottom"""
        status_frame = tk.Frame(self.master, bg=self.colors['primary'], height=35)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        self.lbl_coords = tk.Label(status_frame,
                                  text="📍 Click on map to view coordinates and terrain data  |  Shortcuts: Ctrl+O load, Ctrl+R run, Ctrl+Q quit",
                                  bg=self.colors['primary'],
                                  fg='white',
                                  font=('Segoe UI', 9))
        self.lbl_coords.pack(expand=True, fill=tk.BOTH, padx=20, pady=8)

    def _calculate_slope_aspect_horn(self, dem, pixel_width, pixel_height):
        padded_dem = np.pad(dem, pad_width=1, mode='edge')

        dz_dx = (
            (padded_dem[0:-2, 2:] + 2 * padded_dem[1:-1, 2:] + padded_dem[2:, 2:]) -
            (padded_dem[0:-2, 0:-2] + 2 * padded_dem[1:-1, 0:-2] + padded_dem[2:, 0:-2])
        ) / (8 * 30)

        dz_dy = (
            (padded_dem[2:, 0:-2] + 2 * padded_dem[2:, 1:-1] + padded_dem[2:, 2:]) -
            (padded_dem[0:-2, 0:-2] + 2 * padded_dem[0:-2, 1:-1] + padded_dem[0:-2, 2:])
        ) / (8 * 30)

        slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
        slope_deg = np.degrees(slope_rad)

        # Calculate aspect
        # We use atan2(dz_dx, dz_dy) for a convention where 0 is North.
        aspect_rad = np.arctan2(dz_dx, dz_dy)
        aspect_deg = np.degrees(aspect_rad)

        aspect_deg[aspect_deg < 0] += 360

        aspect_deg[slope_deg < 1e-6] = -1

        nan_mask = np.isnan(dem)
        slope_deg[nan_mask] = np.nan
        aspect_deg[nan_mask] = np.nan

        return slope_deg, aspect_deg

    def load_geotiff(self):
        self.filepath = filedialog.askopenfilename(
            title="Select GeoTIFF File",
            filetypes=(("GeoTIFF files", "*.tif *.tiff"), ("All files", "*.*"))
        )
        if not self.filepath:
            return

        try:
            with rasterio.open(self.filepath) as src:
                self.original_crs = src.crs
                self.transform = src.transform
                dem_data = src.read(1).astype(np.float32)
                self.nodata_value = src.nodata

                if self.nodata_value is not None:
                    dem_data[dem_data == self.nodata_value] = np.nan
                if not self.original_crs:
                    messagebox.showwarning("CRS Warning", "GeoTIFF does not have a CRS defined.")
                if not self.transform:
                    messagebox.showerror("Transform Error", "GeoTIFF does not have a geotransform.")
                    return
                self.pixel_width_m = abs(self.transform.a)
                self.pixel_height_m = abs(self.transform.e)

            # --- Calculate slope and aspect 
            self.slope_degrees, self.aspect_degrees = self._calculate_slope_aspect_horn(
                dem_data, self.pixel_width_m, self.pixel_height_m
            )

            self.lbl_file.config(text=self.filepath.split('/')[-1])
            self.display_slope()
            self.clear_marker_and_packing()

        except Exception as e:
            messagebox.showerror("Error Loading GeoTIFF", f"An error occurred: {e}")
            self.filepath = None
            self.dataset = None
            self.slope_degrees = None
            self.aspect_degrees = None
            self.original_crs = None
            self.transform = None
            self.ax.clear()
            self.canvas.draw()
            self.lbl_file.config(text="No file loaded.")
            self.clear_marker_and_packing()

        self.lbl_file.config(text="📁 TIFF file loaded successfully",
            fg=self.colors['success'])
        pass

    def display_slope(self):
        if self.slope_degrees is None:
            return
        self.ax.clear()
        slope_display = np.copy(self.slope_degrees)
        if self.nodata_value is not None:
            slope_display[np.isnan(self.slope_degrees)] = -9999
        valid_slope = slope_display[slope_display != -9999]
        if valid_slope.size == 0:
            self.ax.text(0.5, 0.5, "No valid slope data to display.", ha='center', va='center')
            self.canvas.draw()
            return
        normalized_slope = (slope_display - np.nanmin(valid_slope)) / (np.nanmax(valid_slope) - np.nanmin(valid_slope))
        normalized_slope = np.nan_to_num(normalized_slope, nan=0)
        img_gray = (normalized_slope * 255).astype(np.uint8)
        self.display_image_rgba = np.zeros((self.slope_degrees.shape[0], self.slope_degrees.shape[1], 4), dtype=np.uint8)
        self.display_image_rgba[..., 0:3] = img_gray[..., np.newaxis]
        self.display_image_rgba[..., 3] = 255
        low_slope_mask = (self.slope_degrees < 5) & (~np.isnan(self.slope_degrees))
        self.display_image_rgba[low_slope_mask, 0] = np.clip(img_gray[low_slope_mask] * 0.3, 0, 255)
        self.display_image_rgba[low_slope_mask, 1] = np.clip(img_gray[low_slope_mask] * 0.7 + 100, 0, 255)
        self.display_image_rgba[low_slope_mask, 2] = np.clip(img_gray[low_slope_mask] * 0.3, 0, 255)
        nan_mask = np.isnan(self.slope_degrees)
        self.display_image_rgba[nan_mask, 3] = 0
        self.ax.imshow(self.display_image_rgba)

        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap='gray', norm=plt.Normalize(vmin=np.nanmin(self.slope_degrees),
                                                                   vmax=np.nanmax(self.slope_degrees)))
        sm.set_array([])
        cb = self.fig.colorbar(sm, ax=self.ax, orientation='horizontal', fraction=0.04, pad=0.08)
        cb.set_label('Slope [degrees]')

        self.ax.set_title("Slope Map (<5° tinted Green)")
        self.ax.set_xlabel("Pixel X")
        self.ax.set_ylabel("Pixel Y")
        self.canvas.draw()

    def _get_aspect_direction(self, degrees):
        """Converts aspect degrees to a compass direction string."""
        if degrees < 0:
            return "Flat"
        if (degrees >= 337.5) or (degrees < 22.5):
            return "N"
        if (degrees >= 22.5) and (degrees < 67.5):
            return "NE"
        if (degrees >= 67.5) and (degrees < 112.5):
            return "E"
        if (degrees >= 112.5) and (degrees < 157.5):
            return "SE"
        if (degrees >= 157.5) and (degrees < 202.5):
            return "S"
        if (degrees >= 202.5) and (degrees < 247.5):
            return "SW"
        if (degrees >= 247.5) and (degrees < 292.5):
            return "W"
        if (degrees >= 292.5) and (degrees < 337.5):
            return "NW"
        return "N/A"

    def on_click_map(self, event):
        if event.inaxes != self.ax:
            return
        if self.transform is None or self.original_crs is None or self.slope_degrees is None:
            self.lbl_coords.config(text="Load GeoTIFF first.")
            return

        col, row = int(round(event.xdata)), int(round(event.ydata))

        if not (0 <= row < self.slope_degrees.shape[0] and 0 <= col < self.slope_degrees.shape[1]):
            self.lbl_coords.config(text="Clicked outside image bounds.")
            return

        self.marker_pixel_coords = (col, row)
        x_coord, y_coord = rasterio.transform.xy(self.transform, row, col, offset='center')

        current_lon, current_lat = x_coord, y_coord
        try:
            if not self.original_crs.is_geographic:
                lons_lats = rasterio.warp.transform(self.original_crs, {'init': 'epsg:4326'}, [x_coord], [y_coord])
                current_lon, current_lat = lons_lats[0][0], lons_lats[1][0]

            self.marker_lon_lat = (current_lon, current_lat)

            slope_val = self.slope_degrees[row, col]
            aspect_val = self.aspect_degrees[row, col]
            slope_text = f"{slope_val:.2f}°" if not np.isnan(slope_val) else "NoData"

            if np.isnan(aspect_val):
                aspect_text = "NoData"
            else:
                direction = self._get_aspect_direction(aspect_val)
                aspect_text = f"{aspect_val:.1f}° ({direction})"

            self.lbl_coords.config(text=f"Lon: {current_lon:.6f}, Lat: {current_lat:.6f} (Slope: {slope_text}, Aspect: {aspect_text})")
            self.lbl_marker_coords.config(text=f"Marker Lon/Lat: {current_lon:.6f}, {current_lat:.6f}")
            self.draw_marker()
            #self.clear_packing_visualization()
            self.lbl_panels_packed.config(text="Packed: N/A")
            self.lbl_annual_energy.config(text="Est. Annual Energy: N/A")

        except Exception as e:
            self.lbl_coords.config(text=f"Coordinate Conversion Error: {e}")
            self.lbl_marker_coords.config(text="Marker Lon/Lat: Error")
            self.marker_lon_lat = None
            self.clear_marker()

    def draw_marker(self):
        self.clear_marker()
        if self.marker_pixel_coords and self.ax:
            col, row = self.marker_pixel_coords
            self.marker_object = self.ax.plot(col, row, 'ro', markersize=8, markeredgecolor='white',
                                              path_effects=[PathEffects.withStroke(linewidth=2, foreground='black')])
            self.canvas.draw_idle()

    def clear_marker(self):
        if self.marker_object:
            try:
                for M in self.marker_object:
                    M.remove()
            except TypeError:
                self.marker_object.remove()
            self.marker_object = None
            self.canvas.draw_idle()

    def clear_packing_visualization(self):
        if self.land_area_rect_patch:
            self.land_area_rect_patch.remove()
            self.land_area_rect_patch = None
        for patch in self.packed_object_patches:
            patch.remove()
        self.packed_object_patches = []
        if self.ax:
            self.canvas.draw_idle()

    def clear_marker_and_packing(self):
        self.clear_marker()
        #self.clear_packing_visualization()
        self.marker_pixel_coords = None
        self.marker_lon_lat = None
        self.lbl_marker_coords.config(text="Marker Lon/Lat: N/A")
        self.lbl_panels_packed.config(text="Packed: N/A")
        self.lbl_annual_energy.config(text="Est. Annual Energy: N/A")
        self.lbl_coords.config(text="Clicked Coordinates: Lon=N/A, Lat=N/A (Slope: N/A, Aspect: N/A)")

    def _validate_energy_inputs(self):
        try:
            efficiency = float(self.entry_panel_efficiency.get())
            perf_ratio = float(self.entry_perf_ratio.get())
            if not (0 < efficiency <= 100):
                raise ValueError("Efficiency must be between 0 and 100%.")
            if not (0 < perf_ratio <= 1):
                raise ValueError("Performance Ratio must be between 0 and 1.")
            return efficiency / 100.0, perf_ratio
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid energy parameters: {e}")
            return None

    def _validate_packing_inputs(self):
        try:
            land_width_m = float(self.entry_land_width.get())
            land_height_m = float(self.entry_land_height.get())
            obj_width_m = float(self.entry_obj_width.get())
            obj_height_m = float(self.entry_obj_height.get())
            num_objects_to_pack = None
            if self.pack_mode.get() == "specify":
                num_objects_to_pack = int(self.entry_num_objects.get())
                if num_objects_to_pack <= 0:
                    raise ValueError("Number of objects must be positive.")
            if not (land_width_m > 0 and land_height_m > 0 and obj_width_m > 0 and obj_height_m > 0):
                raise ValueError("Dimensions must be positive.")
            return land_width_m, land_height_m, obj_width_m, obj_height_m, num_objects_to_pack
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid packing input: {e}")
            return None

    def next_fit_shelf_packing(self, land_width_m, land_height_m, obj_width_m, obj_height_m, num_objects_to_pack=None):
        packed_objects_coords = []
        current_x_m = 0.0
        shelf_bottom_y_m = 0.0
        shelf_effective_height_m = obj_height_m
        objects_placed = 0

        if obj_width_m <= 0 or obj_height_m <= 0:
            return []
        if obj_width_m > land_width_m or obj_height_m > land_height_m:
            return []

        max_iterations = 1_000_000
        iter_count = 0

        while iter_count < max_iterations:
            iter_count += 1
            if num_objects_to_pack is not None and objects_placed >= num_objects_to_pack:
                break

            if shelf_bottom_y_m + shelf_effective_height_m <= land_height_m:
                if current_x_m + obj_width_m <= land_width_m:
                    packed_objects_coords.append({'x': current_x_m, 'y': shelf_bottom_y_m, 'w': obj_width_m, 'h': obj_height_m})
                    current_x_m += obj_width_m
                    objects_placed += 1
                    continue
                else:
                    current_x_m = 0.0
                    shelf_bottom_y_m += shelf_effective_height_m
                    if shelf_bottom_y_m + shelf_effective_height_m <= land_height_m:
                        if current_x_m + obj_width_m <= land_width_m:
                            packed_objects_coords.append({'x': current_x_m, 'y': shelf_bottom_y_m, 'w': obj_width_m, 'h': obj_height_m})
                            current_x_m += obj_width_m
                            objects_placed += 1
                            continue
                        else:
                            break
                    else:
                        break
            else:
                break

        if iter_count >= max_iterations:
            print(f"Warning: Packing reached max iterations ({max_iterations}).")
        return packed_objects_coords

    @functools.lru_cache(maxsize=32)
    def _cached_nasa_call(self, lon, lat):
        base_url = "https://power.larc.nasa.gov/api/temporal/climatology/point"
        params = {
            "parameters": "ALLSKY_SFC_SW_DWN",
            "community": "RE",
            "longitude": f"{lon:.4f}",
            "latitude":  f"{lat:.4f}",
            "format": "JSON"
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        value = data.get("properties", {}).get("parameter", {}).get("ALLSKY_SFC_SW_DWN", {}).get("ANN")
        if value is None or value < 0:
            raise ValueError("Bad NASA response")
        return value

    def fetch_nasa_power_data(self, lon, lat):
        try:
            self.lbl_annual_energy.config(text="Fetching solar data…")
            self.master.update_idletasks()
            return self._cached_nasa_call(round(lon, 4), round(lat, 4))
        except Exception as e:
            messagebox.showerror("NASA POWER Error", str(e))
            return None

    def calculate_and_display_solar_energy(self, num_panels, panel_area_m2):
        if self.marker_lon_lat is None:
            self.lbl_annual_energy.config(text="Est. Annual Energy: Set marker first.")
            return
        if num_panels == 0:
            self.lbl_annual_energy.config(text="Est. Annual Energy: 0 kWh (No panels)")
            return

        energy_inputs = self._validate_energy_inputs()
        if not energy_inputs:
            self.lbl_annual_energy.config(text="Est. Annual Energy: Invalid inputs.")
            return
        panel_efficiency, perf_ratio = energy_inputs

        lon, lat = self.marker_lon_lat
        avg_daily_irradiance_kwh_m2_day = self.fetch_nasa_power_data(lon, lat)

        if avg_daily_irradiance_kwh_m2_day is None:
            self.lbl_annual_energy.config(text="Est. Annual Energy: Solar data unavailable.")
            return

        energy_daily_per_panel_kwh = avg_daily_irradiance_kwh_m2_day * panel_area_m2 * panel_efficiency * perf_ratio
        total_energy_annual_kwh = energy_daily_per_panel_kwh * num_panels * 365

        self.lbl_annual_energy.config(text=f"Est. Annual Energy: {total_energy_annual_kwh:,.2f} kWh")

    def export_results_csv(self):
        if not self.marker_lon_lat:
            messagebox.showwarning("Export", "Run an analysis first.")
            return

        file = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if not file:
            return

        # Retrieve slope & aspect from marker pixel
        col, row = self.marker_pixel_coords
        slope = self.slope_degrees[row, col]
        aspect = self.aspect_degrees[row, col]
        direction = self._get_aspect_direction(aspect) if not np.isnan(aspect) else "NoData"

        with open(file, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["Lon", "Lat", "Slope_deg", "Aspect_direction",
                        "Panels", "Annual_kWh", "Timestamp"])
            lon, lat = self.marker_lon_lat
            txt = self.lbl_annual_energy.cget("text")
            energy = float(txt.split()[3].replace(',', '')) if "kWh" in txt else 0
            panels = self.lbl_panels_packed.cget("text").split()[1]
            w.writerow([lon, lat,
                        f"{slope:.2f}" if not np.isnan(slope) else "NoData",
                        direction,
                        panels,
                        energy,
                        datetime.datetime.utcnow().isoformat(timespec='seconds')])
        messagebox.showinfo("Export", f"Saved to {file}")

    def run_packing_and_energy_simulation(self):
        if not self.marker_pixel_coords:
            messagebox.showerror("Error", "Please click on the map to set a starting marker.")
            return
        if self.transform is None:
            messagebox.showerror("Error", "Load a GeoTIFF first.")
            return

        validated_inputs = self._validate_packing_inputs()
        if not validated_inputs:
            self.lbl_panels_packed.config(text="Packed: Invalid inputs")
            self.lbl_annual_energy.config(text="Est. Annual Energy: N/A")
            return
        land_width_m, land_height_m, panel_width_m, panel_height_m, num_to_pack = validated_inputs

#        self.clear_packing_visualization()

        marker_col_px, marker_row_px = self.marker_pixel_coords
#        land_width_px = land_width_m / self.pixel_width_m
#        land_height_px = land_height_m / self.pixel_height_m

        # Clamp land rectangle to image bounds
#        cols, rows = self.slope_degrees.shape[1], self.slope_degrees.shape[0]
#        marker_col_px = max(0, min(marker_col_px, cols - land_width_px))
#        marker_row_px = max(0, min(marker_row_px, rows - land_height_px))

#        self.land_area_rect_patch = Rectangle((marker_col_px, marker_row_px), land_width_px, land_height_px,
#                                              edgecolor='blue', facecolor='blue', alpha=0.2, linewidth=1.5)
#        self.ax.add_patch(self.land_area_rect_patch)

        packed_objects_meter_coords = self.next_fit_shelf_packing(land_width_m, land_height_m, panel_width_m, panel_height_m, num_to_pack)
        num_panels_packed = len(packed_objects_meter_coords)

        if num_panels_packed == 0:
            status_msg = "No panels could be packed."
            if num_to_pack is not None and num_to_pack > 0:
                status_msg = f"Could not pack the specified {num_to_pack} panels. Packed 0."
            self.lbl_panels_packed.config(text=status_msg)
            self.lbl_annual_energy.config(text="Est. Annual Energy: 0 kWh")
            self.canvas.draw_idle()
            return

#        for obj_m_coords in packed_objects_meter_coords:
            obj_col_px = marker_col_px + (obj_m_coords['x'] / self.pixel_width_m)
            obj_row_px = marker_row_px + (obj_m_coords['y'] / self.pixel_height_m)
            obj_width_px = panel_width_m / self.pixel_width_m
            obj_height_px = panel_height_m / self.pixel_height_m
            obj_patch = Rectangle((obj_col_px, obj_row_px), obj_width_px, obj_height_px,
                                  edgecolor='red', facecolor='red', alpha=0.5, linewidth=1)
            self.ax.add_patch(obj_patch)
            self.packed_object_patches.append(obj_patch)

        status_msg = f"Packed {num_panels_packed} panels."
        if num_to_pack is not None and num_panels_packed < num_to_pack:
            status_msg += f" (Requested: {num_to_pack})"
        self.lbl_panels_packed.config(text=status_msg)
        self.canvas.draw_idle()

        panel_area_m2 = panel_width_m * panel_height_m
        self.calculate_and_display_solar_energy(num_panels_packed, panel_area_m2)


if __name__ == "__main__":
    root = tk.Tk()
    app = GeoTIFFSlopeViewer(root)
    root.bind_all("<Control-o>", lambda e: app.load_geotiff())
    root.bind_all("<Control-r>", lambda e: app.run_packing_and_energy_simulation())
    root.bind_all("<Control-q>", lambda e: root.quit())
    root.mainloop()