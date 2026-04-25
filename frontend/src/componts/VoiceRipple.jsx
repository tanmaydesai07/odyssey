import { useEffect, useRef } from 'react';
import * as THREE from 'three';

const vertexShader = `void main(){gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`;

const fragmentShader = `
precision highp float;
uniform float uTime;
uniform vec2 uResolution;
uniform float uAmplitude;
uniform float uFrequency;
uniform float uRippleRate;
uniform float uWaveAmplitude;
uniform float uWaveFrequency;
uniform vec3 uColor;
uniform float uOpacity;
uniform vec2 uMouse;
uniform float uMouseInfluence;
uniform float uLineWidth;

void main(){
  float pi=3.14159265;
  vec2 uv=gl_FragCoord.xy/uResolution;
  vec2 p=uv*2.0-1.0;
  float aspect=uResolution.x/uResolution.y;
  p.x*=aspect;

  // mouse offset
  p-=uMouse*uMouseInfluence;

  float dist=length(p);

  // Clean concentric rings using sin, then sharpen with pow
  float wave=sin(dist*uFrequency*pi - uRippleRate*uTime);

  // Narrow the lines: raise to high power for thin rings
  float ring=pow(max(wave,0.0), uLineWidth);

  // Fade intensity with distance
  float falloff=uAmplitude/(dist*2.0+1.0);
  ring*=falloff;

  // Soft circular edge fade
  float edge=smoothstep(1.0,0.2,dist);
  ring*=edge;

  // Color
  vec3 col=uColor*(0.7+0.5*ring);
  float a=ring*uOpacity;

  gl_FragColor=vec4(col,a);
}
`;

export default function VoiceRipple({
  color = '#c9a84c',
  speed = 1,
  amplitude = 2.0,
  frequency = 12.69,
  rippleRate = 9.2,
  lineWidth = 8.0,
  opacity = 1,
  followMouse = false,
  mouseInfluence = 0.15,
}) {
  const mountRef = useRef(null);
  const propsRef = useRef(null);
  const mouseRef = useRef([0, 0]);
  const smoothMouseRef = useRef([0, 0]);

  propsRef.current = { color, speed, amplitude, frequency, rippleRate, lineWidth, opacity, followMouse, mouseInfluence };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    let renderer;
    try { renderer = new THREE.WebGLRenderer({ alpha: true, premultipliedAlpha: false }); } catch { return; }
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-0.5, 0.5, 0.5, -0.5, 0.1, 10);
    camera.position.z = 1;

    const uniforms = {
      uTime: { value: 0 },
      uResolution: { value: new THREE.Vector2() },
      uAmplitude: { value: 2.0 },
      uFrequency: { value: 12.69 },
      uRippleRate: { value: 9.2 },
      uLineWidth: { value: 8.0 },
      uColor: { value: new THREE.Color() },
      uOpacity: { value: 1 },
      uMouse: { value: new THREE.Vector2() },
      uMouseInfluence: { value: 0 },
    };

    const material = new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms, transparent: true });
    scene.add(new THREE.Mesh(new THREE.PlaneGeometry(1, 1), material));

    const resize = () => {
      const w = mount.clientWidth, h = mount.clientHeight;
      const dpr = Math.min(window.devicePixelRatio, 2);
      renderer.setSize(w, h);
      renderer.setPixelRatio(dpr);
      uniforms.uResolution.value.set(w * dpr, h * dpr);
    };
    resize();
    window.addEventListener('resize', resize);
    const ro = new ResizeObserver(resize);
    ro.observe(mount);

    const onMM = (e) => {
      const r = mount.getBoundingClientRect();
      mouseRef.current[0] = ((e.clientX - r.left) / r.width - 0.5) * 2;
      mouseRef.current[1] = -((e.clientY - r.top) / r.height - 0.5) * 2;
    };
    mount.addEventListener('mousemove', onMM);

    let fid;
    const animate = (t) => {
      fid = requestAnimationFrame(animate);
      const p = propsRef.current;
      smoothMouseRef.current[0] += (mouseRef.current[0] - smoothMouseRef.current[0]) * 0.06;
      smoothMouseRef.current[1] += (mouseRef.current[1] - smoothMouseRef.current[1]) * 0.06;

      uniforms.uTime.value = t * 0.001 * p.speed;
      uniforms.uAmplitude.value = p.amplitude;
      uniforms.uFrequency.value = p.frequency;
      uniforms.uRippleRate.value = p.rippleRate;
      uniforms.uLineWidth.value = p.lineWidth;
      uniforms.uColor.value.set(p.color);
      uniforms.uOpacity.value = p.opacity;
      uniforms.uMouse.value.set(smoothMouseRef.current[0], smoothMouseRef.current[1]);
      uniforms.uMouseInfluence.value = p.followMouse ? p.mouseInfluence : 0;

      renderer.render(scene, camera);
    };
    fid = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(fid);
      window.removeEventListener('resize', resize);
      ro.disconnect();
      mount.removeEventListener('mousemove', onMM);
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
      renderer.dispose();
      material.dispose();
    };
  }, []);

  return (
    <div ref={mountRef} style={{
      width: '100%', height: '100%',
      overflow: 'visible', background: 'transparent',
    }} />
  );
}
