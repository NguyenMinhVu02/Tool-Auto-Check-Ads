import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { ease, falloff } from './pointerMath.js';

const SPACING = 34;
const RADIUS = 190;
const BASE = new THREE.Color('#7f9fdc');
const HOT = new THREE.Color('#2767d8');

const POINT_VERT = `
uniform vec2 uMouse; uniform float uTime; uniform float uPixel; uniform float uRadius; uniform float uPower;
attribute float aSeed;
varying float vInfluence;
void main() {
  vec2 p = position.xy;
  float d = distance(p, uMouse);
  float f = exp(-pow(d / uRadius, 2.0) * 2.2) * uPower;
  vec2 away = normalize(p - uMouse + vec2(0.0001));
  vec2 drift = vec2(sin(uTime * 0.35 + aSeed * 6.28), cos(uTime * 0.30 + aSeed * 5.1)) * 3.0 * uPower;
  p += away * f * 24.0 + drift;
  vInfluence = f;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 0.0, 1.0);
  gl_PointSize = (2.6 + f * 6.0) * uPixel;
}`;
const POINT_FRAG = `
uniform vec3 uBase; uniform vec3 uHot; varying float vInfluence;
void main() {
  float r = length(gl_PointCoord - 0.5);
  float a = smoothstep(0.5, 0.2, r);
  vec3 col = mix(uBase, uHot, clamp(vInfluence * 1.5, 0.0, 1.0));
  gl_FragColor = vec4(col, a * (0.5 + vInfluence * 0.5));
}`;
const GLOW_VERT = `varying vec2 vPos; void main() { vPos = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const GLOW_FRAG = `
uniform vec2 uMouse; uniform float uRadius; uniform float uPower; uniform vec3 uHot; varying vec2 vPos;
void main() {
  float g = exp(-pow(distance(vPos, uMouse) / (uRadius * 1.7), 2.0));
  gl_FragColor = vec4(uHot, g * 0.2 * uPower);
}`;

function reducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/** Fixed, click-through background: a dot grid that bulges away from the pointer plus a soft spotlight. */
export function PointerField() {
  const host = useRef(null);
  useEffect(() => {
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false, powerPreference: 'low-power' });
    } catch {
      return undefined; // no WebGL: the page simply keeps its flat background
    }
    const still = reducedMotion();
    renderer.setClearColor(0x000000, 0);
    host.current.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(0, 1, 1, 0, -10, 10);
    const uniforms = {
      uMouse: { value: new THREE.Vector2(-9999, -9999) }, uTime: { value: 0 }, uPixel: { value: 1 },
      uRadius: { value: RADIUS }, uPower: { value: 0 }, uBase: { value: BASE }, uHot: { value: HOT },
    };
    let points = null;
    let glow = null;
    const size = { w: 1, h: 1 };
    const build = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      size.w = w;
      size.h = h;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.setSize(w, h, false);
      uniforms.uPixel.value = renderer.getPixelRatio();
      camera.left = 0; camera.right = w; camera.top = h; camera.bottom = 0;
      camera.updateProjectionMatrix();
      if (points) { points.geometry.dispose(); scene.remove(points); }
      if (glow) { glow.geometry.dispose(); scene.remove(glow); }
      const cols = Math.ceil(w / SPACING) + 1;
      const rows = Math.ceil(h / SPACING) + 1;
      const positions = new Float32Array(cols * rows * 3);
      const seeds = new Float32Array(cols * rows);
      for (let r = 0; r < rows; r += 1) {
        for (let c = 0; c < cols; c += 1) {
          const i = r * cols + c;
          positions[i * 3] = c * SPACING + ((r % 2) * SPACING) / 2;
          positions[i * 3 + 1] = r * SPACING;
          seeds[i] = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1;
        }
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 1));
      points = new THREE.Points(geometry, new THREE.ShaderMaterial({
        uniforms, vertexShader: POINT_VERT, fragmentShader: POINT_FRAG, transparent: true, depthWrite: false,
      }));
      glow = new THREE.Mesh(new THREE.PlaneGeometry(w, h).translate(w / 2, h / 2, -1), new THREE.ShaderMaterial({
        uniforms, vertexShader: GLOW_VERT, fragmentShader: GLOW_FRAG, transparent: true, depthWrite: false,
      }));
      scene.add(glow);
      scene.add(points);
    };
    build();

    const target = { x: -9999, y: -9999, power: 0 };
    const current = { x: -9999, y: -9999 };
    const onMove = (event) => {
      if (event.pointerType === 'touch') return;
      if (current.x < -9000) { current.x = event.clientX; current.y = size.h - event.clientY; }
      target.x = event.clientX;
      target.y = size.h - event.clientY;
      target.power = 1;
    };
    const onLeave = () => { target.power = 0; };
    window.addEventListener('pointermove', onMove, { passive: true });
    document.documentElement.addEventListener('pointerleave', onLeave);
    window.addEventListener('blur', onLeave);
    window.addEventListener('resize', build);

    let frame = 0;
    let last = performance.now();
    const render = (now) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      current.x = ease(current.x, target.x, dt);
      current.y = ease(current.y, target.y, dt);
      uniforms.uMouse.value.set(current.x, current.y);
      uniforms.uPower.value = ease(uniforms.uPower.value, target.power, dt, 5);
      uniforms.uTime.value += dt;
      renderer.render(scene, camera);
      if (!still) frame = requestAnimationFrame(render);
    };
    frame = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('pointermove', onMove);
      document.documentElement.removeEventListener('pointerleave', onLeave);
      window.removeEventListener('blur', onLeave);
      window.removeEventListener('resize', build);
      points?.geometry.dispose();
      glow?.geometry.dispose();
      points?.material.dispose();
      glow?.material.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);
  return <div ref={host} className="pointer-field" aria-hidden="true" />;
}

/** Small wireframe gem for the sidebar that turns toward the pointer. */
export function TiltGem({ size = 104 }) {
  const host = useRef(null);
  useEffect(() => {
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' });
    } catch {
      return undefined;
    }
    const still = reducedMotion();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(size, size);
    host.current.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 20);
    camera.position.z = 4.2;
    const geometry = new THREE.IcosahedronGeometry(1.35, 1);
    const wire = new THREE.LineSegments(new THREE.WireframeGeometry(geometry),
      new THREE.LineBasicMaterial({ color: '#8fb4ff', transparent: true, opacity: 0.9 }));
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.62, 0), new THREE.MeshBasicMaterial({ color: '#2767d8', wireframe: true }));
    const group = new THREE.Group();
    group.add(wire, core);
    scene.add(group);
    const aim = { x: 0, y: 0 };
    const onMove = (event) => {
      const box = host.current.getBoundingClientRect();
      const dx = event.clientX - (box.left + box.width / 2);
      const dy = event.clientY - (box.top + box.height / 2);
      aim.x = Math.max(-1, Math.min(1, dx / (window.innerWidth * 0.45)));
      aim.y = Math.max(-1, Math.min(1, dy / (window.innerHeight * 0.45)));
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    let frame = 0;
    let last = performance.now();
    let spin = 0;
    const render = (now) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      spin += dt * 0.35;
      group.rotation.y = ease(group.rotation.y, aim.x * 1.1 + spin, dt, 6);
      group.rotation.x = ease(group.rotation.x, aim.y * 0.8, dt, 6);
      core.rotation.y -= dt * 0.8;
      renderer.render(scene, camera);
      if (!still) frame = requestAnimationFrame(render);
    };
    frame = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('pointermove', onMove);
      [geometry, wire.geometry, core.geometry].forEach((item) => item.dispose());
      [wire.material, core.material].forEach((item) => item.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [size]);
  return <div ref={host} className="tilt-gem" style={{ width: size, height: size }} aria-hidden="true" />;
}
