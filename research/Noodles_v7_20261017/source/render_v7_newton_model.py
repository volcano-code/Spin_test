"""Render actual OBJ as diagnostic views; NOT a synthetic reconstruction of the paper photo."""
from pathlib import Path
import argparse
import vtk
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser();p.add_argument('--initial',type=Path,required=True);p.add_argument('--complete',type=Path,required=True);p.add_argument('--fixed',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)

def render(path,view):
    reader=vtk.vtkOBJReader();reader.SetFileName(str(path));reader.Update()
    rend=vtk.vtkRenderer();rend.SetBackground(.98,.97,.96)
    rw=vtk.vtkRenderWindow();rw.SetOffScreenRendering(True);rw.SetSize(740,740);rw.SetMultiSamples(0);rw.AddRenderer(rend)
    m=vtk.vtkPolyDataMapper();m.SetInputData(reader.GetOutput());actor=vtk.vtkActor();actor.SetMapper(m);actor.GetProperty().SetColor(.91,.34,.1);actor.GetProperty().SetSpecular(.3);actor.GetProperty().SetSpecularPower(30);rend.AddActor(actor)
    cam=rend.GetActiveCamera();bounds=reader.GetOutput().GetBounds();ctr=[(bounds[2*i]+bounds[2*i+1])/2. for i in range(3)];dim=max(bounds[1]-bounds[0],bounds[3]-bounds[2],bounds[5]-bounds[4]);cam.SetFocalPoint(*ctr)
    if view=='perspective':cam.SetPosition(ctr[0]+dim*1.45,ctr[1]-dim*2.6,ctr[2]+dim*1.65)
    elif view=='top':cam.SetPosition(ctr[0],ctr[1],ctr[2]+dim*3.5)
    elif view=='side':cam.SetPosition(ctr[0]+dim*3.5,ctr[1],ctr[2])
    cam.SetViewUp(0,0,1 if view!='top' else 0)
    if view=='top':cam.SetViewUp(0,1,0)
    cam.ParallelProjectionOn();cam.SetParallelScale(dim*.82);rend.ResetCameraClippingRange();rw.Render()
    filt=vtk.vtkWindowToImageFilter();filt.SetInput(rw);filt.ReadFrontBufferOff();filt.Update();writer=vtk.vtkPNGWriter();writer.SetFileName(str(a.out/f'{path.stem}-{view}.png'));writer.SetInputConnection(filt.GetOutputPort());writer.Write();return Image.open(a.out/f'{path.stem}-{view}.png').convert('RGB')

images=[('V7 initial (unoptimized)',render(a.initial,'perspective')),('V7 fixed strands / hub',render(a.fixed,'perspective')),('V7 actual optimized',render(a.complete,'perspective')),('V7 final from above',render(a.complete,'top'))]
w=740;canvas=Image.new('RGB',(w*2,(w+50)*2),'#fafafa');draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',23)
for i,(lab,im) in enumerate(images):
 x=(i%2)*w;y=(i//2)*(w+50)
 draw.text((x+20,y+12),lab,fill='#222',font=font);canvas.paste(im,(x,y+50))
canvas.save(a.out/'v7-actual-newton-visual-comparison.png')
print(a.out/'v7-actual-newton-visual-comparison.png')
