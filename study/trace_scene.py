"""Trusted Manim renderer for algorithm-computed trace states."""
import json
import os
import textwrap
from manim import Scene, Text, VGroup, RoundedRectangle, Transform, UP, DOWN, RIGHT


class StudyTrace(Scene):
    def construct(self):
        self.camera.background_color = '#111827'
        states=json.load(open(os.environ['STUDY_TRACE_SPEC']))
        title=Text('Insertion sort: grow a sorted prefix',font='sans',font_size=30,color='#f1f5f9').to_edge(UP,buff=.55)
        self.add(title)
        held=Text('Held key: none',font='sans',font_size=24,color='#fbbf24').move_to(UP*1.5)
        self.add(held)
        row=VGroup()
        for i,value in enumerate(states[0]['values']):
            box=RoundedRectangle(width=.9,height=.9,corner_radius=.12,color='#64748b')
            number=Text(format(value,'g'),font='sans',font_size=28,color='#f1f5f9').move_to(box)
            index=Text(str(i),font='sans',font_size=16,color='#94a3b8').next_to(box,DOWN,buff=.12)
            item=VGroup(box,number,index)
            row.add(item)
        row.arrange(RIGHT,buff=.14)
        if row.width>12:row.scale_to_fit_width(12)
        self.add(row)
        caption=Text(textwrap.fill(states[0]['note'],66),font='sans',font_size=21,color='#cbd5e1').to_edge(DOWN,buff=.85)
        if caption.width>12:caption.scale_to_fit_width(12)
        self.add(caption)
        counter=Text(f'Step 1 / {len(states)}',font='sans',font_size=17,color='#94a3b8').to_edge(DOWN,buff=.25)
        self.add(counter)
        self.wait(1)
        for step,state in enumerate(states[1:],2):
            animations=[]
            for i,(item,value) in enumerate(zip(row,state['values'])):
                color='#fbbf24' if i in state['focus'] else '#5eead4' if state.get('gap') is None and i<state['prefix'] else '#64748b'
                item[0].set_stroke(color)
                opacity=.4 if i==state.get('gap') else 1
                new=Text(format(value,'g'),font='sans',font_size=28,color='#f1f5f9').move_to(item[1]).set_opacity(opacity)
                animations.append(Transform(item[1],new))
                label=f'{i} gap' if i==state.get('gap') else str(i)
                item[2].become(Text(label,font='sans',font_size=16,color='#fbbf24' if i==state.get('gap') else '#94a3b8').move_to(item[2]))
            key='none' if state['key'] is None else format(state['key'],'g')
            held.become(Text('Held key: '+key,font='sans',font_size=24,color='#fbbf24').move_to(held))
            next_caption=Text(textwrap.fill(state['note'],66),font='sans',font_size=21,color='#cbd5e1').move_to(caption)
            if next_caption.width>12:next_caption.scale_to_fit_width(12)
            # Replace sentences discretely; morphing glyphs produces illegible text.
            caption.become(next_caption)
            counter.become(Text(f'Step {step} / {len(states)}',font='sans',font_size=17,color='#94a3b8').move_to(counter))
            self.play(*animations,run_time=.2)
            self.wait(1.1)
        self.wait(1.5)
