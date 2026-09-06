/* Minimal Cesium type declarations for dynamically loaded CDN script. */
declare namespace Cesium {
  class Viewer {
    constructor(container: string | HTMLElement, options?: Record<string, unknown>);
    scene: Scene;
    destroy(): void;
    canvas: HTMLCanvasElement;
  }
  class Scene {
    camera: Camera;
    globe: Globe;
    primitives: Primitives;
    skyAtmosphere?: unknown;
    skyBox?: unknown;
    context: { canvas: HTMLCanvasElement };
    preRender: { addEventListener(cb: () => void): void; removeEventListener(cb: () => void): void };
    postRender: { addEventListener(cb: () => void): void; removeEventListener(cb: () => void): void };
  }
  class Camera {
    flyTo(options: Record<string, unknown>): void;
    viewRectangle(rectangle: Rectangle, offset?: Record<string, unknown>): void;
    positionCartographic: Cartographic;
  }
  class Globe {
    enableLighting: boolean;
    baseColor: Color;
    depthTestAgainstTerrain: boolean;
  }
  class Primitives {
    add(primitive: unknown): unknown;
    remove(primitive: unknown): boolean;
    removeAll(): void;
  }
  class Rectangle {
    static fromDegrees(west: number, south: number, east: number, north: number): Rectangle;
    west: number;
    south: number;
    east: number;
    north: number;
  }
  class Cartographic {
    longitude: number;
    latitude: number;
    height: number;
    static fromDegrees(longitude: number, latitude: number, height?: number): Cartographic;
  }
  class Cartesian3 {
    x: number;
    y: number;
    z: number;
    static fromDegrees(longitude: number, latitude: number, height?: number): Cartesian3;
  }
  class Color {
    constructor(r?: number, g?: number, b?: number, a?: number);
    static RED: Color;
    static WHITE: Color;
    static withAlpha(color: Color, alpha: number): Color;
  }
  class Entity {
    point?: { pixelSize: number; color: unknown; outlineColor: unknown; outlineWidth: number };
    position?: Cartesian3;
    label?: unknown;
    rectangle?: { coordinates: unknown; material: unknown };
    polyline?: { positions: Cartesian3[]; width: number; material: unknown };
    polygon?: { hierarchy: unknown; material: unknown };
    show?: boolean;
  }
  class PolylineCollection {
    add(options: { positions: Cartesian3[]; width: number; material: unknown }): unknown;
    removeAll(): void;
  }
  class Cartesian2 {
    x: number;
    y: number;
  }
  class ScreenSpaceEventHandler {
    setInputAction(action: (e: unknown) => void, type: number): void;
    destroy(): void;
  }
  class ScreenSpaceEventType {
    static LEFT_CLICK: number;
    static RIGHT_CLICK: number;
    static MOUSE_MOVE: number;
  }
  const defined: (value: unknown) => boolean;
  const when: (promise: unknown) => { then: (cb: (value: unknown) => unknown) => unknown };
}
