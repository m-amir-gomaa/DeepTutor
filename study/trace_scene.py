"""Trusted Manim renderer for algorithm-computed trace states."""
import json
import os
from manim import Scene, Text, VGroup, RoundedRectangle, Transform, UP, DOWN, RIGHT


class StudyTrace(Scene):
    def construct(self):
        self.camera.background_color = '#111827'
        states=json.load(open(os.environ['STUDY_TRACE_SPEC']))
        title=Text('Insertion sort: grow a sorted prefix',font_size=30,color='#f1f5f9').to_edge(UP,buff=.55)
        self.add(title)
        row=VGroup()
        for i,value in enumerate(states[0]['values']):
            box=RoundedRectangle(width=.9,height=.9,corner_radius=.12,color='#64748b')
            number=Text(str(value),font_size=28,color='#f1f5f9').move_to(box)
            item=VGroup(box,number)
            row.add(item)
        row.arrange(RIGHT,buff=.14)
        if row.width>12:row.scale_to_fit_width(12)
        self.add(row)
        caption=Text(states[0]['note'],font_size=20,color='#cbd5e1').to_edge(DOWN,buff=1.1)
        if caption.width>12:caption.scale_to_fit_width(12)
        self.add(caption)
        for state in states[1:]:
            animations=[]
            for i,(item,value) in enumerate(zip(row,state['values'])):
                color='#fbbf24' if i in state['focus'] else '#5eead4' if state.get('gap') is None and i<state['prefix'] else '#64748b'
                item[0].set_stroke(color)
                new=Text(str(value),font_size=28,color='#f1f5f9').move_to(item[1])
                animations.append(Transform(item[1],new))
            note=state['note']+('   Key: '+str(state['key']) if state['key'] is not None else '')
            next_caption=Text(note,font_size=20,color='#cbd5e1').move_to(caption)
            if next_caption.width>12:next_caption.scale_to_fit_width(12)
            animations.append(Transform(caption,next_caption))
            self.play(*animations,run_time=.28)
            self.wait(.28)
        self.wait(1)
