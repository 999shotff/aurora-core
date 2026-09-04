"""3D Globe — WebGL-based Earth visualization using Three.js.

Modular: does not make core geo system depend on 3D.
Uses CDN-loaded Three.js for browser rendering.
"""

from __future__ import annotations

from dataclasses import dataclass

from aurora.geo.domain import BoundingBox


@dataclass(frozen=True)
class GlobeConfig:
    antialias: bool = True
    enable_atmosphere: bool = True
    enable_graticule: bool = False
    background_color: str = "#000011"
    camera_fov: float = 45.0
    camera_near: float = 0.1
    camera_far: float = 1000.0
    min_zoom_distance: float = 1.1
    max_zoom_distance: float = 10.0
    rotation_speed: float = 0.0001
    auto_rotate: bool = False


@dataclass(frozen=True)
class GlobeLayer:
    layer_id: str
    name: str
    visible: bool = True
    opacity: float = 1.0
    layer_type: str = "imagery"
    url: str = ""
    attribution: str = ""


@dataclass(frozen=True)
class SceneFootprint:
    scene_id: str
    bbox: BoundingBox
    acquisition_time: str = ""
    cloud_pct: float = 0.0
    color: str = "#26a69a"
    opacity: float = 0.3


def lat_lon_to_cartesian(
    lat: float, lon: float, radius: float = 1.0
) -> tuple[float, float, float]:
    """Convert lat/lon to 3D Cartesian coordinates on a sphere."""
    import math
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    x = radius * math.cos(lat_rad) * math.cos(lon_rad)
    y = radius * math.sin(lat_rad)
    z = -radius * math.cos(lat_rad) * math.sin(lon_rad)
    return (x, y, z)


def bbox_to_cartesian_corners(
    bbox: BoundingBox, radius: float = 1.001
) -> list[tuple[float, float, float]]:
    """Convert bounding box to 3D corner points."""
    corners = [
        (bbox.south, bbox.west),
        (bbox.south, bbox.east),
        (bbox.north, bbox.east),
        (bbox.north, bbox.west),
    ]
    return [lat_lon_to_cartesian(lat, lon, radius) for lat, lon in corners]


def generate_globe_javascript(config: GlobeConfig | None = None) -> str:
    """Generate the Three.js globe initialization script."""
    cfg = config or GlobeConfig()
    return f"""
(function() {{
    const container = document.getElementById('globe-container');
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color('{cfg.background_color}');

    const camera = new THREE.PerspectiveCamera({cfg.camera_fov}, width / height, {cfg.camera_near}, {cfg.camera_far});
    camera.position.z = 2.5;

    const renderer = new THREE.WebGLRenderer({{ antialias: {str(cfg.antialias).lower()} }});
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const earthGeometry = new THREE.SphereGeometry(1, 64, 64);
    const earthMaterial = new THREE.MeshPhongMaterial({{
        color: 0x223344,
        emissive: 0x112233,
        specular: 0x333333,
        shininess: 25
    }});
    const earth = new THREE.Mesh(earthGeometry, earthMaterial);
    scene.add(earth);

    const wireGeometry = new THREE.SphereGeometry(1.001, 32, 32);
    const wireMaterial = new THREE.MeshBasicMaterial({{
        color: 0x26a69a,
        wireframe: true,
        transparent: true,
        opacity: 0.08
    }});
    const wireframe = new THREE.Mesh(wireGeometry, wireMaterial);
    scene.add(wireframe);

    const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 3, 5);
    scene.add(directionalLight);

    const sunLight = new THREE.PointLight(0xffddaa, 0.4, 100);
    sunLight.position.set(10, 5, 10);
    scene.add(sunLight);

    const starsGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(3000);
    for (let i = 0; i < 3000; i++) {{
        starPositions[i] = (Math.random() - 0.5) * 100;
    }}
    starsGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const starsMaterial = new THREE.PointsMaterial({{ color: 0xffffff, size: 0.1 }});
    const stars = new THREE.Points(starsGeometry, starsMaterial);
    scene.add(stars);

    window._auroraGlobeLayers = {{}};
    window._auroraGlobeAOIs = [];

    window.auroraGlobeAddAOI = function(name, south, west, north, east, color) {{
        const material = new THREE.LineBasicMaterial({{ color: color || 0x26a69a, linewidth: 2 }});
        const points = [
            latLonToCart(south, west), latLonToCart(south, east),
            latLonToCart(north, east), latLonToCart(north, west),
            latLonToCart(south, west)
        ];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, material);
        scene.add(line);
        window._auroraGlobeAOIs.push({{ name, line }});
    }};

    window.auroraGlobeAddFootprint = function(sceneId, south, west, north, east, color, opacity) {{
        const c = color || 0x26a69a;
        const mat = new THREE.MeshBasicMaterial({{
            color: c,
            transparent: true,
            opacity: opacity || 0.3,
            side: THREE.DoubleSide
        }});
        const shape = new THREE.Shape();
        const bl = latLonToCart(south, west);
        const br = latLonToCart(south, east);
        const tr = latLonToCart(north, east);
        const tl = latLonToCart(north, west);
        const geometry = new THREE.BufferGeometry().setFromPoints([bl, br, tr, tl, bl]);
        const mesh = new THREE.Mesh(geometry, mat);
        scene.add(mesh);
    }};

    window.auroraGlobeSetView = function(lat, lon, distance) {{
        const pos = latLonToCart(lat, lon, distance || 2.5);
        camera.position.set(pos[0], pos[1], pos[2]);
        camera.lookAt(0, 0, 0);
    }};

    window.auroraGlobeToggleLayer = function(layerId, visible) {{
        const layer = window._auroraGlobeLayers[layerId];
        if (layer) layer.visible = visible;
    }};

    function latLonToCart(lat, lon, r) {{
        r = r || 1.005;
        const latR = lat * Math.PI / 180;
        const lonR = lon * Math.PI / 180;
        return new THREE.Vector3(
            r * Math.cos(latR) * Math.cos(lonR),
            r * Math.sin(latR),
            -r * Math.cos(latR) * Math.sin(lonR)
        );
    }}

    let isDragging = false;
    let previousMousePosition = {{ x: 0, y: 0 }};

    renderer.domElement.addEventListener('mousedown', (e) => {{
        isDragging = true;
        previousMousePosition = {{ x: e.clientX, y: e.clientY }};
    }});

    renderer.domElement.addEventListener('mousemove', (e) => {{
        if (!isDragging) return;
        const deltaMove = {{
            x: e.clientX - previousMousePosition.x,
            y: e.clientY - previousMousePosition.y
        }};
        earth.rotation.y += deltaMove.x * 0.005;
        earth.rotation.x += deltaMove.y * 0.005;
        wireframe.rotation.y = earth.rotation.y;
        wireframe.rotation.x = earth.rotation.x;
        previousMousePosition = {{ x: e.clientX, y: e.clientY }};
    }});

    renderer.domElement.addEventListener('mouseup', () => {{ isDragging = false; }});
    renderer.domElement.addEventListener('mouseleave', () => {{ isDragging = false; }});

    renderer.domElement.addEventListener('wheel', (e) => {{
        e.preventDefault();
        camera.position.z = Math.max({cfg.min_zoom_distance}, Math.min({cfg.max_zoom_distance}, camera.position.z + e.deltaY * 0.001));
    }}, {{ passive: false }});

    let touchStart = null;
    renderer.domElement.addEventListener('touchstart', (e) => {{
        if (e.touches.length === 1) {{
            touchStart = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
        }}
    }});

    renderer.domElement.addEventListener('touchmove', (e) => {{
        if (!touchStart || e.touches.length !== 1) return;
        e.preventDefault();
        const dx = e.touches[0].clientX - touchStart.x;
        const dy = e.touches[0].clientY - touchStart.y;
        earth.rotation.y += dx * 0.005;
        earth.rotation.x += dy * 0.005;
        wireframe.rotation.y = earth.rotation.y;
        wireframe.rotation.x = earth.rotation.x;
        touchStart = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
    }}, {{ passive: false }});

    renderer.domElement.addEventListener('touchend', () => {{ touchStart = null; }});

    function animate() {{
        requestAnimationFrame(animate);
        if ('{str(cfg.auto_rotate).lower()}' === 'true' && !isDragging) {{
            earth.rotation.y += {cfg.rotation_speed};
            wireframe.rotation.y = earth.rotation.y;
        }}
        renderer.render(scene, camera);
    }}
    animate();

    window.addEventListener('resize', () => {{
        const w = container.clientWidth;
        const h = container.clientHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    }});

    window._auroraGlobeReady = true;
}})();
"""
