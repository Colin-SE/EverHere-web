// 自包含 WebGL 球面，只读取本站的静态陆地纹理。
export async function mountEarth(canvas, onLost) {
  const gl=canvas.getContext('webgl',{alpha:true,antialias:true});
  if(!gl)throw new Error('webgl_unavailable');
  const image=new Image();
  image.src=new URL('../images/earth-land-110m.png',import.meta.url);
  await image.decode();
  if(!canvas.isConnected||gl.isContextLost())return null;

  const shader=(type,source)=>{
    const value=gl.createShader(type);
    gl.shaderSource(value,source);
    gl.compileShader(value);
    if(!gl.getShaderParameter(value,gl.COMPILE_STATUS))throw new Error('earth_shader');
    return value;
  };
  const vertex=shader(gl.VERTEX_SHADER,`
    attribute vec3 point; attribute vec2 uv;
    uniform vec2 yaw; uniform vec2 tilt; uniform vec2 scale;
    varying vec2 mapUV; varying vec3 normal;
    void main(){
      vec3 p=vec3(point.x*yaw.x+point.z*yaw.y,point.y,point.z*yaw.x-point.x*yaw.y);
      normal=vec3(p.x,p.y*tilt.x-p.z*tilt.y,p.z*tilt.x+p.y*tilt.y);
      gl_Position=vec4(normal.xy*scale,-normal.z,1.0);
      mapUV=uv;
    }`);
  const fragment=shader(gl.FRAGMENT_SHADER,`
    precision mediump float;
    uniform sampler2D map; varying vec2 mapUV; varying vec3 normal;
    void main(){
      vec3 n=normalize(normal);
      float light=0.68+0.32*max(dot(n,normalize(vec3(-0.45,0.55,1.0))),0.0);
      float rim=pow(1.0-max(n.z,0.0),3.0);
      gl_FragColor=vec4(texture2D(map,mapUV).rgb*light+rim*vec3(0.06,0.11,0.10),1.0);
    }`);
  const program=gl.createProgram();
  gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);
  gl.deleteShader(vertex);gl.deleteShader(fragment);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('earth_shader');
  gl.useProgram(program);
  const vertices=[],indices=[],rows=36,columns=72;
  for(let y=0;y<=rows;y++){
    const latitude=Math.PI*(0.5-y/rows);
    for(let x=0;x<=columns;x++){
      const longitude=2*Math.PI*(x/columns-0.5);
      vertices.push(Math.cos(latitude)*Math.sin(longitude),Math.sin(latitude),
                    Math.cos(latitude)*Math.cos(longitude),x/columns,y/rows);
      if(y<rows&&x<columns){
        const i=y*(columns+1)+x,j=i+columns+1;
        indices.push(i,j,i+1,j,j+1,i+1);
      }
    }
  }
  const mesh=gl.createBuffer(), faces=gl.createBuffer(), texture=gl.createTexture();
  gl.bindBuffer(gl.ARRAY_BUFFER,mesh);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,faces);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);
  for(const [name,size,offset] of [['point',3,0],['uv',2,12]]){
    const position=gl.getAttribLocation(program,name);
    gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,size,gl.FLOAT,false,20,offset);
  }
  gl.bindTexture(gl.TEXTURE_2D,texture);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.enable(gl.DEPTH_TEST);
  const yaw=gl.getUniformLocation(program,'yaw'),tilt=gl.getUniformLocation(program,'tilt'),scale=gl.getUniformLocation(program,'scale');
  const events=new AbortController(), options={signal:events.signal};
  let rotation=-1.4,pitch=0.18,drag=null,frame=0,last=0,playing=false;
  function draw(){
    const ratio=Math.min(devicePixelRatio||1,1.5);
    const width=Math.max(1,Math.round(canvas.clientWidth*ratio));
    const height=Math.max(1,Math.round(canvas.clientHeight*ratio));
    if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
    gl.viewport(0,0,width,height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    gl.uniform2f(yaw,Math.cos(rotation),Math.sin(rotation));
    gl.uniform2f(tilt,Math.cos(pitch),Math.sin(pitch));
    gl.uniform2f(scale,0.91*Math.min(1,height/width),0.91*Math.min(1,width/height));
    gl.drawElements(gl.TRIANGLES,indices.length,gl.UNSIGNED_SHORT,0);
  }
  function animate(now){
    if(!playing||document.hidden||!canvas.isConnected)return;
    if(!last||now-last>=32){
      rotation+=last?Math.min(now-last,80)*0.00024:0;last=now;draw();
    }
    frame=requestAnimationFrame(animate);
  }
  function play(enabled){
    playing=enabled;last=0;cancelAnimationFrame(frame);
    if(enabled&&!document.hidden)frame=requestAnimationFrame(animate);
  }
  function nudge(x,y){
    rotation+=x;pitch=Math.max(-1.45,Math.min(1.45,pitch+y));draw();
  }
  canvas.addEventListener('pointerdown',event=>{
    canvas.setPointerCapture(event.pointerId);drag=[event.clientX,event.clientY];
  },options);
  canvas.addEventListener('pointermove',event=>{
    if(!drag)return;
    nudge((event.clientX-drag[0])*0.012,(event.clientY-drag[1])*0.012);
    drag=[event.clientX,event.clientY];
  },options);
  canvas.addEventListener('lostpointercapture',()=>{drag=null;},options);
  canvas.addEventListener('keydown',event=>{
    const steps={ArrowLeft:[-0.16,0],ArrowRight:[0.16,0],ArrowUp:[0,-0.14],ArrowDown:[0,0.14]};
    if(!steps[event.key])return;
    event.preventDefault();nudge(...steps[event.key]);
  },options);
  canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();play(false);onLost();},options);
  document.addEventListener('visibilitychange',()=>play(playing),options);
  const resize=new ResizeObserver(draw);resize.observe(canvas);
  draw();
  return {
    play,
    dispose(){play(false);events.abort();resize.disconnect();gl.deleteTexture(texture);gl.deleteBuffer(mesh);gl.deleteBuffer(faces);gl.deleteProgram(program);},
  };
}
