from django import forms
from .models import Group, GroupPost, GroupChatMessage


class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'tag', 'description', 'avatar', 'banner', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название группы'}),
            'tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ТЕГРУППЫ'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Описание...'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'banner': forms.FileInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_tag(self):
        tag = self.cleaned_data['tag'].upper().replace(' ', '')
        return tag


class GroupPostForm(forms.ModelForm):
    class Meta:
        model = GroupPost
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок поста'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Текст поста...'}),
        }


class GroupChatMessageForm(forms.ModelForm):
    class Meta:
        model = GroupChatMessage
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Написать сообщение...',
                'autocomplete': 'off',
                'maxlength': '500',
            })
        }